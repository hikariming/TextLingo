use tauri::{AppHandle, Manager};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::collections::HashMap;

// 插件运行模式
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PluginMode {
    Dev,  // 开发模式：直接调用脚本 (如 python -m ...)
    Prod, // 生产模式：调用打包好的可执行文件
}

// 插件入口配置
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginEntryPoint {
    pub command: String,
    pub args: Vec<String>,
}

// 插件元数据 (对应 plugin.json)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginMetadata {
    pub name: String,
    pub display_name: String,
    pub version: String,
    pub description: String,
    pub entry_points: HashMap<String, PluginEntryPoint>, // "dev", "prod"
    pub release_repo: String,
}

// 插件运行时信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginInfo {
    pub metadata: PluginMetadata,  // Nested, NOT flattened for frontend compatibility
    pub path: String,              // 插件根目录路径
    pub active_mode: PluginMode,   // 当前激活的模式
    pub installed: bool,           // 是否已安装 (用于UI显示)
}

// 插件配置存储 (存放在 plugins.json 或合并在主配置中)
// 这里我们简单起见，从主配置中读取 plugin_modes，或者单独存一个 plugins.json
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PluginConfig {
    pub modes: HashMap<String, PluginMode>, // plugin_name -> active_mode
}

/// 扫描 plugins 目录获取所有插件
/// 扫描 plugins 目录获取所有插件
fn scan_plugins(app_handle: &AppHandle) -> Vec<PluginInfo> {
    let mut all_instances = Vec::new();
    
    let app_data_dir = match app_handle.path().app_data_dir() {
        Ok(dir) => dir,
        Err(_) => return Vec::new(),
    };
    
    // Config
    let plugin_config = load_plugin_config(app_handle).unwrap_or_default();

    // Define paths and their "types"
    // (Path, is_dev_location)
    let mut search_paths = Vec::new();
    
    // 1. AppData/plugins (Prod location)
    let user_plugins_dir = app_data_dir.join("plugins");
    if user_plugins_dir.exists() {
        search_paths.push((user_plugins_dir, false));
    }
    
    // 2. Local/Dev paths
    if let Ok(cwd) = std::env::current_dir() {
        println!("[PluginManager] Current working directory: {:?}", cwd);
        
        // Try ../plugins (e.g. from textlingo-desktop)
        let dev_plugins_dir_1 = cwd.join("../plugins");
        if dev_plugins_dir_1.exists() {
            println!("[PluginManager] Found ../plugins: {:?}", dev_plugins_dir_1);
            search_paths.push((dev_plugins_dir_1, true));
        }

        // Try ../../plugins (e.g. from textlingo-desktop/src-tauri)
        let dev_plugins_dir_2 = cwd.join("../../plugins");
        if dev_plugins_dir_2.exists() {
            println!("[PluginManager] Found ../../plugins: {:?}", dev_plugins_dir_2);
            search_paths.push((dev_plugins_dir_2, true));
        }

        // Try ./plugins
        let local_plugins_dir = cwd.join("plugins");
        if local_plugins_dir.exists() {
            println!("[PluginManager] Found ./plugins: {:?}", local_plugins_dir);
            search_paths.push((local_plugins_dir, true));
        }
    }

    println!("[PluginManager] Scanning paths: {:?}", search_paths);
    // Collect ALL potential plugins
    for (plugins_dir, is_dev_loc) in search_paths {
        if let Ok(entries) = std::fs::read_dir(&plugins_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    let json_path = path.join("plugin.json");
                    if json_path.exists() {
                        if let Ok(content) = std::fs::read_to_string(&json_path) {
                            if let Ok(metadata) = serde_json::from_str::<PluginMetadata>(&content) {
                                let active_mode = plugin_config.modes.get(&metadata.name)
                                    .cloned()
                                    .unwrap_or(PluginMode::Prod);
                                
                                all_instances.push((
                                    PluginInfo {
                                        metadata,
                                        path: path.to_string_lossy().to_string(),
                                        active_mode,
                                        installed: true,
                                    },
                                    is_dev_loc
                                ));
                            }
                        }
                    }
                }
            }
        }
    }

    // Group by name and select best instance
    let mut final_plugins = Vec::new();
    let mut seen_names = std::collections::HashSet::new();
    
    // Get unique names first
    for (p, _) in &all_instances {
        seen_names.insert(p.metadata.name.clone());
    }
    
    for name in seen_names {
        // Find all instances for this name
        let instances: Vec<_> = all_instances.iter()
            .filter(|(p, _)| p.metadata.name == name)
            .collect();
            
        if instances.is_empty() { continue; }
        
        // Get mode from CONFIG, not from instance (instances might have stale mode)
        let active_mode = plugin_config.modes.get(&name)
            .cloned()
            .unwrap_or(PluginMode::Prod);
        
        println!("[PluginManager] Plugin '{}' configured mode: {:?}", name, active_mode);
        
        // Selection Logic:
        // If Mode == Dev, prefer is_dev_loc == true
        // Else, prefer is_dev_loc == false (or just first one)
        
        let selected = if active_mode == PluginMode::Dev {
            // Try to find a dev instance
            instances.iter().find(|&&(_, is_dev)| *is_dev)
                .or_else(|| instances.first()) // Fallback
        } else {
            // Try to find a prod instance (not dev)
            instances.iter().find(|&&(_, is_dev)| !*is_dev)
                .or_else(|| instances.first()) // Fallback
        };
        
        if let Some((info, _)) = selected {
            // Update active_mode to the config value (ensure consistency)
            let mut final_info = info.clone();
            final_info.active_mode = active_mode;
            final_plugins.push(final_info);
        }
    }
    
    // Sort for consistency
    final_plugins.sort_by(|a, b| a.metadata.name.cmp(&b.metadata.name));
    
    println!("[PluginManager] Final plugins list: {} (dev/prod resolved)", final_plugins.len());
    
    final_plugins
}

/// 加载插件配置
fn load_plugin_config(app_handle: &AppHandle) -> Result<PluginConfig, String> {
    let app_data_dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let config_path = app_data_dir.join("plugins_config.json");
    
    if config_path.exists() {
        let content = std::fs::read_to_string(config_path).map_err(|e| e.to_string())?;
        serde_json::from_str(&content).map_err(|e| e.to_string())
    } else {
        Ok(PluginConfig::default())
    }
}

/// 保存插件配置
fn save_plugin_config(app_handle: &AppHandle, config: &PluginConfig) -> Result<(), String> {
    let app_data_dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let config_path = app_data_dir.join("plugins_config.json");
    
    let content = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    std::fs::write(config_path, content).map_err(|e| e.to_string())
}

// ================= Commands =================

#[tauri::command]
pub async fn list_plugins_cmd(app_handle: AppHandle) -> Result<Vec<PluginInfo>, String> {
    Ok(scan_plugins(&app_handle))
}

#[tauri::command]
pub async fn open_plugins_directory(app_handle: AppHandle) -> Result<(), String> {
    let app_data_dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let plugins_dir = app_data_dir.join("plugins");
    
    // Ensure it exists
    if !plugins_dir.exists() {
        std::fs::create_dir_all(&plugins_dir).map_err(|e| e.to_string())?;
    }
    
    #[cfg(target_os = "macos")]
    std::process::Command::new("open")
        .arg(&plugins_dir)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "windows")]
    std::process::Command::new("explorer")
        .arg(&plugins_dir)
        .spawn()
        .map_err(|e| e.to_string())?;
        
    Ok(())
}

#[tauri::command]
pub async fn set_plugin_mode_cmd(
    app_handle: AppHandle,
    plugin_name: String,
    mode: String,
) -> Result<(), String> {
    let mut config = load_plugin_config(&app_handle)?;
    
    let mode_enum = match mode.as_str() {
        "dev" => PluginMode::Dev,
        "prod" => PluginMode::Prod,
        _ => return Err("Invalid mode".to_string()),
    };
    
    config.modes.insert(plugin_name.clone(), mode_enum);
    save_plugin_config(&app_handle, &config)?;
    
    Ok(())
}

#[tauri::command]
pub async fn get_plugin_modes_cmd(app_handle: AppHandle) -> Result<HashMap<String, PluginMode>, String> {
    let config = load_plugin_config(&app_handle)?;
    Ok(config.modes)
}

/// 获取插件执行命令
/// 给后端其他模块调用
pub fn get_plugin_execution_command(
    app_handle: &AppHandle,
    plugin_name: &str,
) -> Result<(String, Vec<String>, std::path::PathBuf), String> {
    let plugins = scan_plugins(app_handle);
    let plugin = plugins.iter()
        .find(|p| p.metadata.name == plugin_name)
        .ok_or(format!("Plugin '{}' not found", plugin_name))?;

    let entry_point = match plugin.active_mode {
        PluginMode::Dev => plugin.metadata.entry_points.get("dev"),
        PluginMode::Prod => plugin.metadata.entry_points.get("prod"),
    }.ok_or(format!("Entry point for mode '{:?}' not found", plugin.active_mode))?;

    let plugin_dir = PathBuf::from(&plugin.path);
    let mut command = entry_point.command.clone();
    
    // 如果是 Prod 模式且命令以 ./ 开头，解析为绝对路径
    if plugin.active_mode == PluginMode::Prod && command.starts_with("./") {
        let exe_name = &command[2..]; // remove ./
        
        // 适配不同操作系统
        #[cfg(target_os = "windows")]
        let exe_name = format!("{}.exe", exe_name);
        // 如果有后缀，这里可以扩展逻辑

        let exe_path = plugin_dir.join(exe_name);
        if !exe_path.exists() {
             // 尝试查找带平台后缀的可执行文件
             // e.g. openkoto-pdf-translator-macos-arm64
             // 这里可以加入更复杂的查找逻辑，或者在 plugin.json 中就写死 generic name，靠重命名解决
             // 目前假设 plugin.json 写的是 "./openkoto-pdf-translator"
             // 我们可以尝试查找目录下的可执行文件
             return Err(format!("Executable not found at {:?}", exe_path));
        }
        command = exe_path.to_string_lossy().to_string();
    }
    
    Ok((command, entry_point.args.clone(), plugin_dir))
}
