use tauri::{AppHandle, Manager, Emitter};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::collections::HashMap;
use futures_util::StreamExt;
use reqwest::Client;
use std::io::Write;

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

// ================= 插件自动安装相关 =================

/// GitHub Release 信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginReleaseInfo {
    pub version: String,
    pub download_url: String,
    pub file_name: String,
    pub file_size: u64,
}

/// 安装进度事件
#[derive(Debug, Clone, Serialize)]
pub struct InstallProgress {
    pub stage: String,      // "downloading" | "installing" | "completed" | "failed"
    pub progress: f64,      // 0.0 - 1.0
    pub message: String,
}

/// 获取当前平台对应的资源名
fn get_platform_asset_name() -> &'static str {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => "openkoto-pdf-translator-macos-arm64",
        ("macos", _) => "openkoto-pdf-translator-macos-x64",
        ("windows", _) => "openkoto-pdf-translator-win-x64.exe",
        ("linux", _) => "openkoto-pdf-translator-linux-x64",
        _ => "unknown",
    }
}

/// 内置的 plugin.json 内容
fn get_builtin_plugin_json() -> &'static str {
    r#"{
    "name": "openkoto-pdf-translator",
    "display_name": "PDF 翻译插件",
    "version": "0.1.0",
    "description": "提供本地 PDF 文档的翻译功能，支持生成纯译文和双语对照版。",
    "entry_points": {
        "prod": {
            "command": "./openkoto-pdf-translator",
            "args": []
        }
    },
    "release_repo": "hikariming/openkoto"
}"#
}

/// 检查插件是否已安装
#[tauri::command]
pub async fn check_plugin_installed_cmd(
    app_handle: AppHandle,
    plugin_name: String,
) -> Result<bool, String> {
    let app_data_dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let plugin_dir = app_data_dir.join("plugins").join(&plugin_name);

    // 检查 plugin.json 是否存在
    let plugin_json_exists = plugin_dir.join("plugin.json").exists();

    // 检查可执行文件是否存在
    let exe_name = if cfg!(target_os = "windows") {
        "openkoto-pdf-translator.exe"
    } else {
        "openkoto-pdf-translator"
    };
    let exe_exists = plugin_dir.join(exe_name).exists();

    // 也检查开发目录
    if plugin_json_exists && exe_exists {
        return Ok(true);
    }

    // 检查开发模式的目录
    let plugins = scan_plugins(&app_handle);
    let is_installed = plugins.iter().any(|p| p.metadata.name == plugin_name);

    Ok(is_installed)
}

/// 从 GitHub API 获取最新 release 信息
#[tauri::command]
pub async fn get_plugin_release_info_cmd(
    release_repo: String,
) -> Result<PluginReleaseInfo, String> {
    let client = Client::builder()
        .user_agent("OpenKoto-Desktop")
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let api_url = format!("https://api.github.com/repos/{}/releases/latest", release_repo);

    let response = client.get(&api_url)
        .send()
        .await
        .map_err(|e| format!("网络请求失败: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("GitHub API 返回错误: {}", response.status()));
    }

    let release: serde_json::Value = response.json()
        .await
        .map_err(|e| format!("解析响应失败: {}", e))?;

    let version = release["tag_name"]
        .as_str()
        .unwrap_or("unknown")
        .to_string();

    // 找到匹配当前平台的 asset
    let platform_asset_name = get_platform_asset_name();

    let assets = release["assets"]
        .as_array()
        .ok_or("未找到发布资源")?;

    let asset = assets.iter()
        .find(|a| {
            a["name"].as_str()
                .map(|name| name.contains(platform_asset_name))
                .unwrap_or(false)
        })
        .ok_or(format!("未找到适用于当前系统 ({}) 的插件版本", platform_asset_name))?;

    let download_url = asset["browser_download_url"]
        .as_str()
        .ok_or("未找到下载链接")?
        .to_string();

    let file_name = asset["name"]
        .as_str()
        .unwrap_or("plugin")
        .to_string();

    let file_size = asset["size"]
        .as_u64()
        .unwrap_or(0);

    Ok(PluginReleaseInfo {
        version,
        download_url,
        file_name,
        file_size,
    })
}

/// 下载并安装插件
#[tauri::command]
pub async fn install_plugin_cmd(
    app_handle: AppHandle,
    download_url: String,
    plugin_name: String,
) -> Result<(), String> {
    let app_data_dir = app_handle.path().app_data_dir().map_err(|e| e.to_string())?;
    let plugins_dir = app_data_dir.join("plugins");
    let plugin_dir = plugins_dir.join(&plugin_name);

    // 创建目录
    std::fs::create_dir_all(&plugin_dir)
        .map_err(|e| format!("创建插件目录失败: {}", e))?;

    // 发送开始下载事件
    let _ = app_handle.emit("plugin-install-progress", InstallProgress {
        stage: "downloading".to_string(),
        progress: 0.0,
        message: "正在下载插件...".to_string(),
    });

    // 下载文件
    let client = Client::builder()
        .user_agent("OpenKoto-Desktop")
        .build()
        .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

    let response = client.get(&download_url)
        .send()
        .await
        .map_err(|e| format!("下载失败: {}", e))?;

    if !response.status().is_success() {
        return Err(format!("下载失败: HTTP {}", response.status()));
    }

    let total_size = response.content_length().unwrap_or(0);

    // 确定目标文件名
    let exe_name = if cfg!(target_os = "windows") {
        "openkoto-pdf-translator.exe"
    } else {
        "openkoto-pdf-translator"
    };
    let exe_path = plugin_dir.join(exe_name);

    // 流式下载并显示进度
    let mut file = std::fs::File::create(&exe_path)
        .map_err(|e| format!("创建文件失败: {}", e))?;

    let mut downloaded: u64 = 0;
    let mut stream = response.bytes_stream();

    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result.map_err(|e| format!("下载中断: {}", e))?;
        file.write_all(&chunk)
            .map_err(|e| format!("写入文件失败: {}", e))?;

        downloaded += chunk.len() as u64;

        let progress = if total_size > 0 {
            downloaded as f64 / total_size as f64
        } else {
            0.5
        };

        let _ = app_handle.emit("plugin-install-progress", InstallProgress {
            stage: "downloading".to_string(),
            progress,
            message: format!("下载中... {:.1}%", progress * 100.0),
        });
    }

    drop(file);

    // 发送安装中事件
    let _ = app_handle.emit("plugin-install-progress", InstallProgress {
        stage: "installing".to_string(),
        progress: 0.9,
        message: "正在安装...".to_string(),
    });

    // 设置可执行权限 (macOS/Linux)
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = std::fs::metadata(&exe_path)
            .map_err(|e| format!("获取文件权限失败: {}", e))?
            .permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&exe_path, perms)
            .map_err(|e| format!("设置可执行权限失败: {}", e))?;
    }

    // 写入 plugin.json
    let plugin_json_path = plugin_dir.join("plugin.json");
    std::fs::write(&plugin_json_path, get_builtin_plugin_json())
        .map_err(|e| format!("写入 plugin.json 失败: {}", e))?;

    // 发送完成事件
    let _ = app_handle.emit("plugin-install-progress", InstallProgress {
        stage: "completed".to_string(),
        progress: 1.0,
        message: "安装完成！".to_string(),
    });

    println!("[PluginManager] Plugin '{}' installed successfully at {:?}", plugin_name, plugin_dir);

    Ok(())
}
