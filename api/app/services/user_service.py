import os
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, UploadFile
from supabase import Client
import structlog

from app.schemas.user import (
    UserProfileUpdate, 
    UserSubscriptionCreate, 
    UserSubscriptionUpdate,
    UserCompleteProfile,
    ProfileSetupRequest,
    ProfileSetupResponse,
    UserLingoCloudStats,
    ArticlesStats,
    NovelsStats,
    ModelInfo,
    MembershipLimits
)
from app.services.supabase_client import supabase_service
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger_for_service("user_service")


class UserService:
    """User service class"""
    
    def __init__(self, access_token: str = None):
        """
        Initialize user service
        
        Args:
            access_token: User access token, if provided uses user client (follows RLS), otherwise uses service role client
        """
        if access_token:
            # Use user client, follows RLS policies
            self.supabase = supabase_service.get_user_client(access_token)
            self.access_token = access_token
            self.use_service_role = False
            if LoggingConfig.should_log_debug():
                logger.info("UserService initialized with user token (RLS enabled)")
        else:
            # Use service role client, bypass RLS (backward compatibility)
            self.supabase = supabase_service.get_client()
            self.access_token = None
            self.use_service_role = True
            if LoggingConfig.should_log_debug():
                logger.info("UserService initialized with service role (RLS bypassed)")
            
        # Always keep service client reference for fallback
        self.service_client = supabase_service.get_client()
        self.avatar_bucket = "avatars"
        self._ensure_bucket_exists()
    
    def _execute_with_fallback(self, operation_name: str, user_id: str, primary_operation, fallback_operation=None):
        """
        Execute database operation, use fallback operation if primary operation fails
        
        Args:
            operation_name: Operation name for logging
            user_id: User ID
            primary_operation: Primary operation function
            fallback_operation: Fallback operation function (optional)
        
        Returns:
            Operation result
        """
        try:
            if LoggingConfig.should_log_rls_debug():
                logger.debug(f"[RLS_FALLBACK] Attempting primary operation {operation_name}: user_id={user_id}, use_service_role={self.use_service_role}")
            result = primary_operation()
            if LoggingConfig.should_log_rls_debug():
                logger.debug(f"[RLS_FALLBACK] Primary operation {operation_name} succeeded: user_id={user_id}")
            return result
        except Exception as primary_error:
            if LoggingConfig.should_log_rls_debug():
                logger.warning(f"[RLS_FALLBACK] Primary operation {operation_name} failed: user_id={user_id}, error={str(primary_error)}")
            
            # If not using service role and has fallback operation
            if not self.use_service_role and fallback_operation:
                try:
                    if LoggingConfig.should_log_rls_debug():
                        logger.debug(f"[RLS_FALLBACK] Attempting fallback operation {operation_name} (service role): user_id={user_id}")
                    result = fallback_operation()
                    if LoggingConfig.should_log_rls_debug():
                        logger.debug(f"[RLS_FALLBACK] Fallback operation {operation_name} succeeded: user_id={user_id}")
                    return result
                except Exception as fallback_error:
                    LoggingConfig.log_error_with_context(logger, fallback_error, {
                        "operation": operation_name,
                        "user_id": user_id,
                        "context": "RLS_FALLBACK - Both primary and fallback operations failed"
                    })
                    raise fallback_error
            else:
                # No fallback operation or already using service role, raise original error
                raise primary_error

    def _ensure_bucket_exists(self):
        """Ensure avatar storage bucket exists"""
        try:
            # Try to list buckets to check if it exists
            buckets = self.supabase.storage.list_buckets()
            bucket_exists = any(bucket.name == self.avatar_bucket for bucket in buckets if hasattr(bucket, 'name'))
            
            if not bucket_exists:
                # Try to create bucket (may require admin permissions)
                try:
                    self.supabase.storage.create_bucket(
                        self.avatar_bucket,
                        options={
                            "public": True,
                            "file_size_limit": 5242880,  # 5MB
                            "allowed_mime_types": ["image/jpeg", "image/png", "image/gif", "image/webp"]
                        }
                    )
                except Exception:
                    # Creation failed, possibly due to insufficient permissions or bucket already exists, continue
                    pass
        except Exception:
            # If check fails, continue execution, let upload handle the error
            pass

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user complete profile information"""
        try:
            if LoggingConfig.should_log_rls_debug():
                logger.debug(f"[RLS_DEBUG] Starting to get user profile: user_id={user_id}, use_service_role={self.use_service_role}, has_access_token={self.access_token is not None}")
            
            # First try to get from user_complete_profiles view (with fallback)
            def query_complete_profiles():
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Attempting to get data from user_complete_profiles view: user_id={user_id}")
                response = self.supabase.table("user_complete_profiles")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] user_complete_profiles query result: data_count={len(response.data) if response.data else 0}")
                return response
            
            def query_complete_profiles_fallback():
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Using service_client to get data from user_complete_profiles view: user_id={user_id}")
                response = self.service_client.table("user_complete_profiles")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] service_client user_complete_profiles query result: data_count={len(response.data) if response.data else 0}")
                return response
            
            try:
                response = self._execute_with_fallback(
                    "query user_complete_profiles view",
                    user_id,
                    query_complete_profiles,
                    query_complete_profiles_fallback
                )
                
                if response.data:
                    profile = response.data[0]
                    if LoggingConfig.should_log_rls_debug():
                        logger.debug(f"[RLS_DEBUG] Got user profile from view: profile_keys={list(profile.keys()) if profile else []}")
                    
                    # Supplement with Supabase auth user information
                    try:
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Attempting to get auth info using service_client: user_id={user_id}")
                        user_response = self.service_client.auth.admin.get_user_by_id(user_id)
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] service_client auth query result: user_found={user_response.user is not None}")
                        if user_response.user:
                            # Ensure email field exists and is not empty
                            if not profile.get("email") and user_response.user.email:
                                profile["email"] = user_response.user.email
                            
                            # If full_name is empty, get from auth
                            if not profile.get("full_name") and user_response.user.user_metadata:
                                auth_full_name = user_response.user.user_metadata.get("full_name")
                                if auth_full_name:
                                    profile["full_name"] = auth_full_name
                    except Exception as auth_error:
                        if LoggingConfig.should_log_rls_debug():
                            logger.warning(f"[RLS_DEBUG] service_client auth query failed: {str(auth_error)}")
                        pass  # Ignore auth retrieval errors, continue returning profile
                    
                    if LoggingConfig.should_log_rls_debug():
                        logger.debug(f"[RLS_DEBUG] Successfully returning user profile from view: user_id={user_id}")
                    return profile
            except Exception as view_error:
                # If view query completely fails, fallback to basic table query
                if LoggingConfig.should_log_rls_debug():
                    logger.warning(f"[RLS_DEBUG] user_complete_profiles view query completely failed: {str(view_error)}")
                pass
            
            # Fallback plan: get user info from basic table (with fallback)
            def query_user_profiles():
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Querying from basic table user_profiles: user_id={user_id}")
                response = self.supabase.table("user_profiles")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] user_profiles query result: data_count={len(response.data) if response.data else 0}")
                return response
            
            def query_user_profiles_fallback():
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Using service_client to query from user_profiles: user_id={user_id}")
                response = self.service_client.table("user_profiles")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] service_client user_profiles query result: data_count={len(response.data) if response.data else 0}")
                return response
            
            profile_response = self._execute_with_fallback(
                "query user_profiles table",
                user_id,
                query_user_profiles,
                query_user_profiles_fallback
            )
            
            if not profile_response.data:
                # User profile does not exist, try to auto-create default profile
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] User profile does not exist, attempting to auto-create: user_id={user_id}")
                
                try:
                    # STEP 1: Get user from auth
                    try:
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Step 1: Get auth info before creating profile: user_id={user_id}")
                        service_client = supabase_service.get_client()
                        user_response = service_client.auth.admin.get_user_by_id(user_id)
                        if not user_response.user:
                            logger.error(f"[RLS_DEBUG] User does not exist in auth system: user_id={user_id}")
                            return None
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Step 1 Succeeded: Got auth user info: email={user_response.user.email}")
                    except Exception as auth_error:
                        logger.error(f"[RLS_DEBUG] FAILED at Step 1 (get_user_by_id): {str(auth_error)}", user_id=user_id, exc_info=True)
                        raise Exception(f"Failed to get user from auth: {str(auth_error)}")

                    auth_user = user_response.user
                    user_metadata = auth_user.user_metadata or {}
                    
                    # Create default profile data
                    default_profile_data = {
                        'user_id': user_id,
                        'email': auth_user.email,  # Ensure email field exists
                        'full_name': user_metadata.get('full_name') or user_metadata.get('name') or auth_user.email.split('@')[0],
                        'role': 'free',
                        'points': 350,  # Default points for new users
                        'native_language': 'zh',  # Default Chinese
                        'learning_language': 'en',  # Default learning English
                        'language_level': 'beginner',  # Default beginner level
                        'bio': '',
                        'avatar_url': user_metadata.get('avatar_url') or user_metadata.get('picture'),
                        'profile_setup_completed': False,  # New field
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    
                    # Multi-layer fallback strategy for creating user profile
                    def create_via_rpc():
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Attempting to create user profile via RPC: user_id={user_id}")
                        response = self.service_client.rpc('create_user_profile_bypass_rls', {
                            'p_user_id': user_id,
                            'p_full_name': user_metadata.get('full_name') or user_metadata.get('name') or auth_user.email.split('@')[0],
                            'p_role': 'free',
                            'p_points': 350,
                            'p_native_language': 'zh',
                            'p_learning_language': 'en',
                            'p_language_level': 'beginner',
                            'p_bio': '',
                            'p_avatar_url': user_metadata.get('avatar_url') or user_metadata.get('picture'),
                            'p_profile_setup_completed': False
                        }).execute()
                        
                        if response.data and len(response.data) > 0 and response.data[0].get('success'):
                            if LoggingConfig.should_log_rls_debug():
                                logger.debug(f"[RLS_DEBUG] RPC user profile creation succeeded: user_id={user_id}")
                            return response
                        else:
                            error_msg = response.data[0].get('message') if response.data and response.data[0] else 'No data or success=false in response'
                            logger.error(f"[RLS_DEBUG] RPC user profile creation failed: user_id={user_id}, error='{error_msg}', full_response={response}")
                            raise Exception(f"RPC call failed or returned success=false: {error_msg}")
                    
                    def create_via_service_insert():
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Attempting service role direct insert: user_id={user_id}")
                        response = self.service_client.table("user_profiles").insert(default_profile_data).execute()
                        if response.data:
                            if LoggingConfig.should_log_rls_debug():
                                logger.debug(f"[RLS_DEBUG] Service role direct insert succeeded: user_id={user_id}")
                            return response
                        else:
                            logger.error(f"[RLS_DEBUG] Service role direct insert failed, no data returned: user_id={user_id}, response={response}")
                            if hasattr(response, 'error') and response.error:
                                raise Exception(f"Direct insert with service role failed: {response.error.message}")
                            raise Exception("Direct insert with service role returned no data.")
                    
                    def create_via_user_insert():
                        if self.use_service_role:
                            raise Exception("Cannot use user token when service role is forced")
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Attempting user token insert: user_id={user_id}")
                        response = self.supabase.table("user_profiles").insert(default_profile_data).execute()
                        if not response.data:
                            logger.error(f"[RLS_DEBUG] User token insert failed, no data returned: user_id={user_id}")
                            raise Exception("Direct insert with user token returned no data.")
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] User token insert succeeded: user_id={user_id}")
                        logger.info(f"Successfully created default profile for user {user_id} with their own token.")
                        return response
                    
                    # Try creation methods by priority
                    creation_methods = [
                        ("RPC method", create_via_rpc),
                        ("Service Role direct insert", create_via_service_insert),
                        ("User Token insert", create_via_user_insert)
                    ]
                    
                    created = False
                    last_error = None
                    
                    for method_name, method_func in creation_methods:
                        try:
                            if LoggingConfig.should_log_rls_debug():
                                logger.debug(f"[RLS_DEBUG] Step 2: Attempting {method_name}: user_id={user_id}")
                            method_func()
                            created = True
                            if LoggingConfig.should_log_rls_debug():
                                logger.debug(f"[RLS_DEBUG] {method_name} succeeded: user_id={user_id}")
                            break
                        except Exception as method_error:
                            last_error = method_error
                            logger.warning(f"[RLS_DEBUG] {method_name} failed: user_id={user_id}, error={str(method_error)}", exc_info=True)
                            continue
                    
                    if not created:
                        logger.error(f"[RLS_DEBUG] All creation methods failed: user_id={user_id}, last_error={str(last_error)}")
                        raise Exception(f"All profile creation methods failed. Last error: {str(last_error)}")

                    # Re-retrieve the created profile (with fallback)
                    def retrieve_created_profile():
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Re-retrieving newly created user profile: user_id={user_id}")
                        response = self.supabase.table("user_profiles")\
                            .select("*")\
                            .eq("user_id", user_id)\
                            .execute()
                        if not response.data:
                            raise Exception("Failed to retrieve newly created profile")
                        return response
                    
                    def retrieve_created_profile_fallback():
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Using service_client to re-retrieve newly created user profile: user_id={user_id}")
                        response = self.service_client.table("user_profiles")\
                            .select("*")\
                            .eq("user_id", user_id)\
                            .execute()
                        if not response.data:
                            raise Exception("Failed to retrieve newly created profile with service client")
                        return response
                    
                    try:
                        profile_response = self._execute_with_fallback(
                            "re-retrieve created profile",
                            user_id,
                            retrieve_created_profile,
                            retrieve_created_profile_fallback
                        )
                        if LoggingConfig.should_log_rls_debug():
                            logger.debug(f"[RLS_DEBUG] Successfully re-retrieved newly created user profile: user_id={user_id}")
                    except Exception as retrieve_error:
                        logger.error(f"[RLS_DEBUG] Unable to re-retrieve newly created user profile: user_id={user_id}, error={str(retrieve_error)}")
                        logger.error(f"Failed to retrieve newly created profile for user {user_id}")
                        return None
                        
                except Exception as create_error:
                    logger.error(f"[RLS_DEBUG] FINAL CATCH: Error occurred during default profile creation process: user_id={user_id}, error={str(create_error)}", exc_info=True)
                    logger.error(f"Error creating default profile for user {user_id}: {create_error}")
                    raise HTTPException(status_code=500, detail=f"Profile creation failed: {str(create_error)}")
                
            profile = profile_response.data[0]
            
            # Get user info from Supabase auth, use service role to ensure permissions
            try:
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Supplementing auth info for existing profile: user_id={user_id}")
                service_client = supabase_service.get_client()
                user_response = service_client.auth.admin.get_user_by_id(user_id)
                if user_response.user:
                    # Ensure email field exists and is not empty
                    if not profile.get("email") and user_response.user.email:
                        profile["email"] = user_response.user.email
                    
                    # If full_name is empty, get from auth
                    if user_response.user.user_metadata:
                        auth_full_name = user_response.user.user_metadata.get("full_name")
                        if auth_full_name and not profile.get("full_name"):
                            profile["full_name"] = auth_full_name
            except Exception as auth_supplement_error:
                logger.warning(f"[RLS_DEBUG] Failed to supplement auth info: user_id={user_id}, error={str(auth_supplement_error)}")
                pass  # Ignore auth retrieval errors
            
            # Get subscription info (with fallback)
            def query_subscription():
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Getting user subscription info: user_id={user_id}")
                response = self.supabase.table("user_subscriptions")\
                    .select("plan_type, plan_name, status, end_date")\
                    .eq("user_id", user_id)\
                    .eq("status", "active")\
                    .execute()
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Subscription info query result: data_count={len(response.data) if response.data else 0}")
                return response
            
            def query_subscription_fallback():
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Using service_client to get user subscription info: user_id={user_id}")
                response = self.service_client.table("user_subscriptions")\
                    .select("plan_type, plan_name, status, end_date")\
                    .eq("user_id", user_id)\
                    .eq("status", "active")\
                    .execute()
                if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] service_client subscription info query result: data_count={len(response.data) if response.data else 0}")
                return response
            
            try:
                subscription_response = self._execute_with_fallback(
                    "query user subscription info",
                    user_id,
                    query_subscription,
                    query_subscription_fallback
                )
                
                if subscription_response.data:
                    sub = subscription_response.data[0]
                    profile["plan_type"] = sub.get("plan_type")
                    profile["plan_name"] = sub.get("plan_name")
                    profile["subscription_status"] = sub.get("status")
                    profile["subscription_end_date"] = sub.get("end_date")
                else:
                    # Default free plan
                    profile["plan_type"] = "free"
                    profile["plan_name"] = "Free Plan"
                    profile["subscription_status"] = "active"
                    profile["subscription_end_date"] = None
            except Exception as sub_error:
                # Default free plan
                logger.warning(f"[RLS_DEBUG] Getting subscription info completely failed, using default values: user_id={user_id}, error={str(sub_error)}")
                profile["plan_type"] = "free"
                profile["plan_name"] = "Free Plan"
                profile["subscription_status"] = "active"
                profile["subscription_end_date"] = None
            
            if LoggingConfig.should_log_rls_debug():
                    logger.debug(f"[RLS_DEBUG] Successfully returning user profile: user_id={user_id}")
            return profile
            
        except Exception as e:
            logger.error(f"[RLS_DEBUG] Overall failure getting user profile: user_id={user_id}, error={str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get user information: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user information by email"""
        try:
            # Use Supabase Admin API to get user list, then manually filter
            # Note: list_users() does not support email parameter filtering
            response = self.service_client.auth.admin.list_users(page=1, per_page=1000)
            
            # Check response format and extract users
            if hasattr(response, 'users'):
                users = response.users
            elif isinstance(response, list):
                users = response
            else:
                users = []
            
            # Find matching email in user list
            for user in users:
                if hasattr(user, 'email') and user.email == email:
                    return {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.user_metadata.get("full_name") if user.user_metadata else None,
                        "email_confirmed_at": user.email_confirmed_at,
                        "created_at": user.created_at,
                        "updated_at": user.updated_at,
                    }
            
            # If not found above, try backup method
            # Backup method: query user_profiles table (as fallback, not preferred)
            try:
                profile_response = self.supabase.table("user_profiles")\
                    .select("user_id, email")\
                    .eq("email", email)\
                    .limit(1)\
                    .execute()
                
                if profile_response.data:
                    profile = profile_response.data[0]
                    # Note: Data returned here is incomplete because profiles table lacks auth info
                    # But sufficient for token-login flow to determine user exists
                    return {
                        "id": profile.get("user_id"),
                        "email": profile.get("email"),
                    }
            except Exception as profile_error:
                print(f"Profile query backup method failed for {email}: {profile_error}")
            
            # If all methods fail to find, return None
            return None
            
        except Exception as e:
            # 记录详细错误
            print(f"An unexpected error occurred in get_user_by_email for {email}: {e}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: UserProfileUpdate) -> Dict[str, Any]:
        """Update user basic profile information"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            profile_dict = profile_data.dict(exclude_unset=True)
            logger.info(f"Updating profile for user {user_id} with data: {profile_dict}, use_service_role: {self.use_service_role}")
            
            # Separate full_name and other fields
            full_name = profile_dict.pop('full_name', None)
            other_fields = {k: v for k, v in profile_dict.items() if v is not None}
            
            if not full_name and not other_fields:
                logger.warning(f"No data to update for user {user_id}")
                raise HTTPException(status_code=400, detail="No data to update")

            # Update Supabase Auth full_name (displayname) - always use service role
            if full_name is not None:
                try:
                    logger.info(f"Updating Supabase auth displayname for user {user_id} to: {full_name}")
                    # Use service role client for auth operations
                    service_client = supabase_service.get_client()
                    user_response = service_client.auth.admin.get_user_by_id(user_id)
                    if not user_response.user:
                        logger.error(f"User {user_id} not found in Supabase auth")
                        raise HTTPException(status_code=404, detail="User not found in authentication system")
                    
                    # Update full_name in user_metadata (this updates displayname)
                    current_metadata = user_response.user.user_metadata or {}
                    current_metadata['full_name'] = full_name
                    
                    auth_update_response = service_client.auth.admin.update_user_by_id(
                        user_id,
                        {
                            "user_metadata": current_metadata
                        }
                    )
                    
                    if not auth_update_response.user:
                        logger.error(f"Failed to update auth metadata for user {user_id}")
                        raise HTTPException(status_code=500, detail="Failed to update user display name")
                    
                    logger.info(f"Successfully updated Supabase auth displayname for user {user_id}")
                    
                except HTTPException:
                    raise
                except Exception as auth_error:
                    error_str = str(auth_error)
                    logger.error(f"Auth update error for user {user_id}: {error_str}")
                    
                    # Check common permission errors
                    if "User not allowed" in error_str or "not authorized" in error_str.lower():
                        logger.warning(f"Permission denied for auth update, user {user_id} might need to re-login")
                        # For permission errors, we still try to continue updating database profile
                        # But record warning information
                        pass
                    elif "not found" in error_str.lower():
                        raise HTTPException(status_code=404, detail="User not found in authentication system")
                    else:
                        raise HTTPException(status_code=500, detail=f"Failed to update user display name: {error_str}")

            # Update other fields in database
            if other_fields:
                try:
                    logger.info(f"Updating database profile for user {user_id} with fields: {other_fields}")
                    response = self.supabase.table("user_profiles")\
                        .update(other_fields)\
                        .eq("user_id", user_id)\
                        .execute()

                    if not response.data:
                        logger.warning(f"No user profile found in database for user {user_id}, attempting to create one with service role")
                        # If user profile doesn't exist, force create using service role
                        try:
                            # Use service role client to get user info and create profile
                            service_client = supabase_service.get_client()
                            user_response = service_client.auth.admin.get_user_by_id(user_id)
                            if not user_response.user:
                                logger.error(f"User {user_id} not found in auth system")
                                raise HTTPException(status_code=404, detail="User not found in authentication system")
                            
                            user = user_response.user
                            # Create default profile data
                            default_profile = {
                                'user_id': user_id,
                                'email': user.email,
                                'full_name': user.user_metadata.get('full_name') or user.user_metadata.get('name') if user.user_metadata else None,
                                'role': 'free',
                                'points': 350,
                                'interface_language': other_fields.get('interface_language', 'zh'),
                                'native_language': other_fields.get('native_language', 'zh'),
                                'learning_language': 'en',  # Default learning English
                                'language_level': 'beginner',  # Default beginner level
                                'bio': other_fields.get('bio', ''),
                                'avatar_url': user.user_metadata.get('avatar_url') or user.user_metadata.get('picture') if user.user_metadata else None,
                                'profile_setup_completed': False,  # New field
                                'created_at': datetime.utcnow().isoformat(),
                                'updated_at': datetime.utcnow().isoformat()
                            }
                            
                            # Merge fields to update
                            default_profile.update(other_fields)
                            
                            # Force create profile using service role, bypass RLS
                            try:
                                logger.info(f"Attempting to create profile with service role for user {user_id}")
                                create_response = service_client.table("user_profiles").insert(default_profile).execute()
                                
                                if create_response.data:
                                    logger.info(f"Successfully created user profile for {user_id} via service role")
                                else:
                                    raise Exception("Service role insert failed")
                                        
                            except Exception as create_error:
                                logger.error(f"Failed to create user profile for {user_id}: {create_error}")
                                # If creation fails, still throw 404 error
                                raise HTTPException(status_code=404, detail="User profile does not exist and cannot be auto-created")
                                
                        except HTTPException:
                            raise
                        except Exception as auto_create_error:
                            logger.error(f"Auto-create profile failed for user {user_id}: {auto_create_error}")
                            raise HTTPException(status_code=404, detail="User profile does not exist")
                    
                    logger.info(f"Successfully updated database profile for user {user_id}")
                    
                except HTTPException:
                    raise
                except Exception as db_error:
                    logger.error(f"Database update error for user {user_id}: {str(db_error)}")
                    raise HTTPException(status_code=500, detail=f"Failed to update user profile database: {str(db_error)}")

            # Return updated complete information
            logger.info(f"Profile update completed for user {user_id}, fetching updated profile")
            updated_profile = await self.get_user_profile(user_id)
            if not updated_profile:
                logger.error(f"Failed to fetch updated profile for user {user_id}")
                raise HTTPException(status_code=500, detail="Unable to fetch updated user information")
            
            return updated_profile
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating profile for user {user_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error occurred while updating user information: {str(e)}")

    async def upload_avatar(self, user_id: str, file: UploadFile) -> Dict[str, str]:
        """Upload user avatar to Supabase Storage"""
        try:
            # Validate filename
            if not file.filename:
                raise HTTPException(status_code=400, detail="Filename cannot be empty")

            # Generate unique filename and determine correct MIME type
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'jpg'
            file_name = f"{user_id}/{uuid.uuid4()}.{file_extension}"
            
            # Determine correct MIME type based on file extension
            mime_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg', 
                'png': 'image/png',
                'gif': 'image/gif',
                'webp': 'image/webp'
            }
            
            correct_mime_type = mime_type_map.get(file_extension)
            if not correct_mime_type:
                raise HTTPException(status_code=400, detail=f"Unsupported file format: {file_extension}. Supported formats: jpg, jpeg, png, gif, webp")
            
            # Validate or correct file type
            if not file.content_type or not file.content_type.startswith('image/'):
                # If no correct content_type, use our determined type
                final_content_type = correct_mime_type
            else:
                # Use file's original MIME type, but ensure it's a supported image type
                if file.content_type in ['image/jpeg', 'image/png', 'image/gif', 'image/webp']:
                    final_content_type = file.content_type
                else:
                    # If not a supported type, fallback to extension-based type
                    final_content_type = correct_mime_type

            # Reset file pointer and read file content
            await file.seek(0)
            file_content = await file.read()
            
            # Validate file content
            if not file_content:
                raise HTTPException(status_code=400, detail="File content is empty")
                
            if not isinstance(file_content, bytes):
                # Try to convert to bytes
                if isinstance(file_content, str):
                    file_content = file_content.encode('utf-8')
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid file content type: {type(file_content)}")
            
            if len(file_content) == 0:
                raise HTTPException(status_code=400, detail="File is empty")

            # Upload to Supabase Storage  
            try:
                # First delete existing file (if any)
                try:
                    self.supabase.storage.from_(self.avatar_bucket).remove([file_name])
                except:
                    pass  # Ignore deletion errors, file may not exist
                
                # Upload file with correct MIME type
                response = self.supabase.storage.from_(self.avatar_bucket).upload(
                    file_name,
                    file_content,
                    file_options={
                        "content-type": final_content_type
                    }
                )
            except Exception as upload_error:
                raise HTTPException(status_code=500, detail=f"Storage upload exception: {str(upload_error)}")

            # Check upload response
            if response is None:
                raise HTTPException(status_code=500, detail="Upload failed: response is empty")
            
            # Check if there are errors
            if hasattr(response, 'error') and response.error:
                error_msg = str(response.error) if response.error else "Unknown upload error"
                raise HTTPException(status_code=500, detail=f"Upload failed: {error_msg}")
            
            # Check response data
            if hasattr(response, 'data') and not response.data:
                raise HTTPException(status_code=500, detail="Upload failed: no response data")

            # Get public URL
            try:
                public_url = self.supabase.storage.from_(self.avatar_bucket).get_public_url(file_name)
            except Exception as url_error:
                raise HTTPException(status_code=500, detail=f"Get URL exception: {str(url_error)}")
            
            # Check if returned URL is valid
            if not public_url or not isinstance(public_url, str):
                raise HTTPException(status_code=500, detail="Failed to get avatar URL")
            
            if not public_url.strip():
                raise HTTPException(status_code=500, detail="Retrieved avatar URL is empty")

            # Update user avatar URL
            try:
                update_response = self.supabase.table("user_profiles")\
                    .update({"avatar_url": public_url})\
                    .eq("user_id", user_id)\
                    .execute()

                if not update_response.data:
                    raise HTTPException(status_code=500, detail="Failed to update avatar URL")
            except Exception as db_error:
                raise HTTPException(status_code=500, detail=f"Database update exception: {str(db_error)}")

            return {
                "avatar_url": public_url,
                "message": "Avatar uploaded successfully"
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Avatar upload failed: {str(e)}")

    async def delete_avatar(self, user_id: str) -> Dict[str, str]:
        """Delete user avatar"""
        try:
            # Get current avatar URL
            profile = await self.get_user_profile(user_id)
            if not profile or not profile.get("avatar_url"):
                raise HTTPException(status_code=404, detail="User has no avatar")

            # Extract file path from URL
            avatar_url = profile["avatar_url"]
            if self.avatar_bucket in avatar_url:
                file_path = avatar_url.split(f"{self.avatar_bucket}/")[-1]
                
                # Delete file from Storage
                self.supabase.storage.from_(self.avatar_bucket).remove([file_path])

            # Clear avatar URL in database
            self.supabase.table("user_profiles")\
                .update({"avatar_url": None})\
                .eq("user_id", user_id)\
                .execute()

            return {"message": "Avatar deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Avatar deletion failed: {str(e)}")

    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user subscription information"""
        try:
            response = self.supabase.table("user_subscriptions")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get subscription information: {str(e)}")

    async def create_subscription(self, user_id: str, subscription_data: UserSubscriptionCreate) -> Dict[str, Any]:
        """Create user subscription"""
        try:
            # Cancel existing active subscription first
            self.supabase.table("user_subscriptions")\
                .update({"status": "cancelled"})\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()

            # Create new subscription
            new_subscription = {
                "user_id": user_id,
                **subscription_data.dict()
            }

            response = self.supabase.table("user_subscriptions")\
                .insert(new_subscription)\
                .execute()

            if not response.data:
                raise HTTPException(status_code=500, detail="Failed to create subscription")

            return response.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")

    async def update_subscription(self, user_id: str, subscription_data: UserSubscriptionUpdate) -> Dict[str, Any]:
        """Update user subscription"""
        try:
            update_data = subscription_data.dict(exclude_unset=True)
            if not update_data:
                raise HTTPException(status_code=400, detail="No subscription data to update")

            response = self.supabase.table("user_subscriptions")\
                .update(update_data)\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()

            if not response.data:
                raise HTTPException(status_code=404, detail="No active subscription found")

            return response.data[0]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")

    async def cancel_subscription(self, user_id: str) -> Dict[str, str]:
        """Cancel user subscription"""
        try:
            response = self.supabase.table("user_subscriptions")\
                .update({"status": "cancelled"})\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()

            if not response.data:
                raise HTTPException(status_code=404, detail="No active subscription found")

            return {"message": "Subscription cancelled"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")

    async def update_user_points(self, user_id: str, points_change: int) -> Dict[str, Any]:
        """Update user points"""
        try:
            # Get current points
            current_profile = await self.get_user_profile(user_id)
            if not current_profile:
                raise HTTPException(status_code=404, detail="User does not exist")

            new_points = current_profile["points"] + points_change
            if new_points < 0:
                raise HTTPException(status_code=400, detail="Insufficient points")

            # Update points
            response = self.supabase.table("user_profiles")\
                .update({"points": new_points})\
                .eq("user_id", user_id)\
                .execute()

            if not response.data:
                raise HTTPException(status_code=500, detail="Failed to update points")

            return {
                "old_points": current_profile["points"],
                "new_points": new_points,
                "change": points_change
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update points: {str(e)}")

    async def complete_profile_setup(self, user_id: str, setup_data: ProfileSetupRequest) -> ProfileSetupResponse:
        """Complete user initial setup (mainly for Google login users to set language preferences for the first time)"""
        try:
            logger.info(f"User {user_id} starting to complete initial setup: {setup_data.dict()}")
            
            # Validate language codes
            allowed_languages = ['zh', 'en', 'ja', 'ko', 'es', 'fr', 'de', 'it', 'pt', 'ru']
            if setup_data.native_language not in allowed_languages:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported native language code: {setup_data.native_language}. Supported languages: {allowed_languages}"
                )
            
            if setup_data.learning_language and setup_data.learning_language not in allowed_languages:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported learning language code: {setup_data.learning_language}. Supported languages: {allowed_languages}"
                )
            
            # Validate language level
            allowed_levels = ['beginner', 'intermediate', 'advanced', 'native']
            if setup_data.language_level and setup_data.language_level not in allowed_levels:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported language level: {setup_data.language_level}. Supported levels: {allowed_levels}"
                )
            
            # Use database function to complete setup, ensure atomic operation
            try:
                response = self.supabase.rpc('complete_user_profile_setup', {
                    'p_user_id': user_id,
                    'p_native_language': setup_data.native_language,
                    'p_learning_language': setup_data.learning_language or 'en',
                    'p_language_level': setup_data.language_level or 'beginner'
                }).execute()
                
                if response.data and len(response.data) > 0:
                    result = response.data[0]
                    if result.get('success'):
                        logger.info(f"User {user_id} initial setup completed successfully")
                        
                        # Get updated user profile
                        updated_profile = await self.get_user_profile(user_id)
                        
                        return ProfileSetupResponse(
                            success=True,
                            message="Initial setup completed successfully!",
                            profile=updated_profile
                        )
                    else:
                        error_msg = result.get('message', 'Setup failed')
                        logger.error(f"User {user_id} initial setup failed: {error_msg}")
                        raise HTTPException(status_code=500, detail=error_msg)
                else:
                    raise Exception("Database function returned empty result")
                    
            except Exception as rpc_error:
                logger.warning(f"RPC method failed, attempting direct update: {rpc_error}")
                
                # Fallback to direct update
                update_data = {
                    'native_language': setup_data.native_language,
                    'learning_language': setup_data.learning_language or 'en',
                    'language_level': setup_data.language_level or 'beginner',
                    'profile_setup_completed': True,
                    'updated_at': datetime.utcnow().isoformat()
                }
                
                response = self.supabase.table("user_profiles")\
                    .update(update_data)\
                    .eq("user_id", user_id)\
                    .execute()
                
                if not response.data:
                    logger.error(f"User {user_id} profile does not exist, cannot complete setup")
                    raise HTTPException(status_code=404, detail="User profile does not exist")
                
                logger.info(f"User {user_id} initial setup completed successfully (direct update)")
                
                # Get updated user profile
                updated_profile = await self.get_user_profile(user_id)
                
                return ProfileSetupResponse(
                    success=True,
                    message="Initial setup completed successfully!",
                    profile=updated_profile
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error occurred while user {user_id} completing initial setup: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to complete initial setup: {str(e)}")

    async def get_lingocloud_stats(self, user_id: str) -> UserLingoCloudStats:
        """获取用户LingoCloud综合统计信息"""
        try:
            logger.info(f"Getting LingoCloud stats for user: {user_id}")
            
            # 获取用户基本信息
            profile = await self.get_user_profile(user_id)
            if not profile:
                raise HTTPException(status_code=404, detail="用户信息不存在")
            
            # 1. 获取文章统计
            from app.services.material_service import material_service
            try:
                articles_data = await material_service.get_user_articles_stats(user_id, self.access_token)
                articles_stats = ArticlesStats(**articles_data)
            except Exception as e:
                logger.warning(f"Failed to get articles stats: {e}")
                articles_stats = ArticlesStats(
                    total_articles=0,
                    public_articles=0,
                    private_articles=0,
                    by_status={},
                    by_difficulty={},
                    by_category={}
                )
            
            # 2. 获取小说统计
            from app.services.novel_service import novel_service
            try:
                novels_data = await novel_service.get_user_novel_stats(user_id, self.access_token)
                novels_stats = NovelsStats(
                    total_novels=novels_data.total_novels,
                    public_novels=novels_data.public_novels,
                    private_novels=novels_data.private_novels,
                    total_chapters=novels_data.total_chapters,
                    by_language=novels_data.by_language
                )
            except Exception as e:
                logger.warning(f"Failed to get novels stats: {e}")
                novels_stats = NovelsStats(
                    total_novels=0,
                    public_novels=0,
                    private_novels=0,
                    total_chapters=0,
                    by_language={}
                )
            
            # 3. 获取可用模型
            from app.services.enhanced_ai_service import enhanced_ai_service
            try:
                user_subscription = profile.get("plan_type", "free")
                models_data = await enhanced_ai_service.get_available_models(user_subscription)
                available_models = [
                    ModelInfo(
                        id=model["id"],
                        name=model["name"],
                        provider=model["provider"],
                        description=model["description"],
                        capabilities=model["capabilities"],
                        required_tier=model.get("required_tier", "free"),
                        points_per_1k_tokens=model.get("points_cost", {}).get("per_1k_tokens"),
                        available=model.get("available", True)
                    ) for model in models_data
                ]
            except Exception as e:
                logger.warning(f"Failed to get available models: {e}")
                available_models = []
            
            # 4. 定义会员限额
            plan_type = profile.get("plan_type", "free")
            membership_limits = self._get_membership_limits(plan_type)
            
            # 5. 计算使用情况对比限额
            usage_vs_limits = self._calculate_usage_vs_limits(
                articles_stats, novels_stats, membership_limits
            )
            
            return UserLingoCloudStats(
                user_id=user_id,
                email=profile["email"],
                full_name=profile.get("full_name"),
                plan_type=plan_type,
                role=profile["role"],
                points=profile["points"],
                articles_stats=articles_stats,
                novels_stats=novels_stats,
                available_models=available_models,
                membership_limits=membership_limits,
                usage_vs_limits=usage_vs_limits
            )
            
        except Exception as e:
            logger.error(f"Error getting LingoCloud stats: {e}", user_id=user_id)
            raise

    def _get_membership_limits(self, plan_type: str) -> MembershipLimits:
        """获取会员限额信息"""
        limits_config = {
            "free": {
                "plan_name": "免费版",
                "limits": {
                    "articles": 5,
                    "novels": 2,
                    "flashcards": 1000,
                    "article_segments": 400,
                    "novel_size_mb": 5,
                    "models": ["T2"],
                    "monthly_credits": 1000
                }
            },
            "plus": {
                "plan_name": "PLUS版", 
                "limits": {
                    "articles": 20,
                    "novels": 20,
                    "flashcards": "unlimited",
                    "article_segments": 800,
                    "novel_size_mb": 15,
                    "models": ["T1", "T2"],
                    "monthly_credits": 20000
                }
            },
            "pro": {
                "plan_name": "PRO版",
                "limits": {
                    "articles": 50,
                    "novels": 50, 
                    "flashcards": "unlimited",
                    "article_segments": 1200,
                    "novel_size_mb": 30,
                    "models": ["T1", "T2"],
                    "monthly_credits": 30000
                }
            },
            "max": {
                "plan_name": "MAX版",
                "limits": {
                    "articles": 200,
                    "novels": 200,
                    "flashcards": "unlimited", 
                    "article_segments": 2000,
                    "novel_size_mb": 50,
                    "models": ["T1", "T2"],
                    "monthly_credits": 60000
                }
            }
        }
        
        config = limits_config.get(plan_type, limits_config["free"])
        return MembershipLimits(
            plan_type=plan_type,
            plan_name=config["plan_name"],
            limits=config["limits"]
        )

    def _calculate_usage_vs_limits(self, articles_stats: ArticlesStats, novels_stats: NovelsStats, limits: MembershipLimits) -> Dict[str, Any]:
        """计算使用情况对比限额"""
        usage = {
            "articles": {
                "used": articles_stats.total_articles,
                "limit": limits.limits.get("articles", 0),
                "percentage": 0,
                "is_over_limit": False
            },
            "novels": {
                "used": novels_stats.total_novels,
                "limit": limits.limits.get("novels", 0),
                "percentage": 0,
                "is_over_limit": False
            }
        }
        
        # 计算文章使用率
        if usage["articles"]["limit"] > 0:
            usage["articles"]["percentage"] = min(100, (usage["articles"]["used"] / usage["articles"]["limit"]) * 100)
            usage["articles"]["is_over_limit"] = usage["articles"]["used"] > usage["articles"]["limit"]
        
        # 计算小说使用率
        if usage["novels"]["limit"] > 0:
            usage["novels"]["percentage"] = min(100, (usage["novels"]["used"] / usage["novels"]["limit"]) * 100)
            usage["novels"]["is_over_limit"] = usage["novels"]["used"] > usage["novels"]["limit"]
        
        return usage


# Create global user service instance (backward compatible, uses service role)
user_service = UserService() 