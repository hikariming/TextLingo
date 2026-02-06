import { useEffect, useState, useRef } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogFooter } from '../ui/dialog';
import { Button } from '../ui/button';
import { Download, CheckCircle, AlertCircle, Loader2, FileText } from 'lucide-react';

interface PluginReleaseInfo {
    version: string;
    download_url: string;
    file_name: string;
    file_size: number;
}

interface InstallProgress {
    stage: 'downloading' | 'installing' | 'completed' | 'failed';
    progress: number;
    message: string;
}

interface PluginInstallDialogProps {
    isOpen: boolean;
    onClose: () => void;
    onInstallComplete: () => void;
}

type InstallState = 'idle' | 'loading' | 'ready' | 'downloading' | 'installing' | 'completed' | 'error';

export function PluginInstallDialog({ isOpen, onClose, onInstallComplete }: PluginInstallDialogProps) {
    const { t } = useTranslation();
    const [state, setState] = useState<InstallState>('idle');
    const [releaseInfo, setReleaseInfo] = useState<PluginReleaseInfo | null>(null);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [error, setError] = useState<string | null>(null);

    const pluginName = 'openkoto-pdf-translator';
    const releaseRepo = 'hikariming/openkoto';

    // 使用 ref 避免 effect 因 callback 变化而重新注册
    const onInstallCompleteRef = useRef(onInstallComplete);
    onInstallCompleteRef.current = onInstallComplete;

    // 获取 release 信息
    useEffect(() => {
        if (isOpen && state === 'idle') {
            fetchReleaseInfo();
        }
    }, [isOpen]);

    // 监听安装进度事件
    useEffect(() => {
        if (!isOpen) return;

        let unlistenFn: (() => void) | null = null;

        const setup = async () => {
            unlistenFn = await listen<InstallProgress>('plugin-install-progress', (event) => {
                const { stage, progress, message } = event.payload;
                setProgress(progress);
                setProgressMessage(message);

                if (stage === 'downloading') {
                    setState('downloading');
                } else if (stage === 'installing') {
                    setState('installing');
                } else if (stage === 'completed') {
                    setState('completed');
                    // 延迟关闭并回调
                    setTimeout(() => {
                        onInstallCompleteRef.current();
                    }, 1500);
                } else if (stage === 'failed') {
                    setState('error');
                    setError(message);
                }
            });
        };

        setup();

        return () => {
            if (unlistenFn) unlistenFn();
        };
    }, [isOpen]);

    // 重置状态
    useEffect(() => {
        if (!isOpen) {
            setState('idle');
            setReleaseInfo(null);
            setProgress(0);
            setProgressMessage('');
            setError(null);
        }
    }, [isOpen]);

    const fetchReleaseInfo = async () => {
        setState('loading');
        setError(null);

        try {
            const info = await invoke<PluginReleaseInfo>('get_plugin_release_info_cmd', {
                releaseRepo
            });
            setReleaseInfo(info);
            setState('ready');
        } catch (err) {
            setError(String(err));
            setState('error');
        }
    };

    const handleInstall = async () => {
        if (!releaseInfo) return;

        try {
            setState('downloading');
            setProgress(0);
            setProgressMessage(t('pluginInstall.startingDownload', '正在开始下载...'));

            await invoke('install_plugin_cmd', {
                downloadUrl: releaseInfo.download_url,
                pluginName
            });
        } catch (err) {
            setError(String(err));
            setState('error');
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const renderContent = () => {
        switch (state) {
            case 'idle':
            case 'loading':
                return (
                    <div className="flex flex-col items-center py-8">
                        <Loader2 className="w-12 h-12 text-primary animate-spin mb-4" />
                        <p className="text-muted-foreground">
                            {t('pluginInstall.fetchingInfo', '正在获取插件信息...')}
                        </p>
                    </div>
                );

            case 'ready':
                return (
                    <div className="space-y-4">
                        <div className="flex items-start gap-4 p-4 bg-muted/30 rounded-lg">
                            <div className="p-3 bg-primary/10 rounded-lg">
                                <FileText className="w-8 h-8 text-primary" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-semibold text-lg">PDF 翻译插件</h3>
                                <p className="text-sm text-muted-foreground mt-1">
                                    {t('pluginInstall.description', '提供本地 PDF 文档的翻译功能，支持生成纯译文和双语对照版。')}
                                </p>
                                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                                    <span>{t('pluginInstall.version', '版本')}: {releaseInfo?.version}</span>
                                    <span>{t('pluginInstall.size', '大小')}: {formatFileSize(releaseInfo?.file_size || 0)}</span>
                                </div>
                            </div>
                        </div>

                        <p className="text-sm text-muted-foreground">
                            {t('pluginInstall.installNote', '点击安装后将自动下载并配置插件，完成后即可使用 PDF 翻译功能。')}
                        </p>
                    </div>
                );

            case 'downloading':
            case 'installing':
                return (
                    <div className="space-y-4 py-4">
                        <div className="flex items-center gap-3">
                            <Loader2 className="w-5 h-5 text-primary animate-spin" />
                            <span className="font-medium">{progressMessage}</span>
                        </div>

                        {/* 进度条 */}
                        <div className="w-full bg-muted rounded-full h-2.5 overflow-hidden">
                            <div
                                className="bg-primary h-full transition-all duration-300 ease-out"
                                style={{ width: `${Math.min(progress * 100, 100)}%` }}
                            />
                        </div>

                        <p className="text-xs text-muted-foreground text-center">
                            {t('pluginInstall.doNotClose', '请勿关闭此窗口...')}
                        </p>
                    </div>
                );

            case 'completed':
                return (
                    <div className="flex flex-col items-center py-8">
                        <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
                        <h3 className="font-semibold text-lg">
                            {t('pluginInstall.success', '安装成功！')}
                        </h3>
                        <p className="text-muted-foreground mt-2">
                            {t('pluginInstall.startingTranslation', '即将开始翻译...')}
                        </p>
                    </div>
                );

            case 'error':
                return (
                    <div className="space-y-4">
                        <div className="flex items-start gap-3 p-4 bg-destructive/10 rounded-lg">
                            <AlertCircle className="w-5 h-5 text-destructive mt-0.5 shrink-0" />
                            <div>
                                <h4 className="font-medium text-destructive">
                                    {t('pluginInstall.errorTitle', '安装失败')}
                                </h4>
                                <p className="text-sm text-muted-foreground mt-1">{error}</p>
                            </div>
                        </div>

                        <p className="text-sm text-muted-foreground">
                            {t('pluginInstall.errorHint', '请检查网络连接后重试，或前往 GitHub 手动下载插件。')}
                        </p>
                    </div>
                );
        }
    };

    const renderFooter = () => {
        switch (state) {
            case 'idle':
            case 'loading':
                return (
                    <Button variant="outline" onClick={onClose} disabled>
                        {t('common.cancel', '取消')}
                    </Button>
                );

            case 'ready':
                return (
                    <>
                        <Button variant="outline" onClick={onClose}>
                            {t('common.cancel', '取消')}
                        </Button>
                        <Button onClick={handleInstall} className="gap-2">
                            <Download size={16} />
                            {t('pluginInstall.install', '安装插件')}
                        </Button>
                    </>
                );

            case 'downloading':
            case 'installing':
                return (
                    <Button variant="outline" disabled>
                        {t('pluginInstall.installing', '安装中...')}
                    </Button>
                );

            case 'completed':
                return null;

            case 'error':
                return (
                    <>
                        <Button variant="outline" onClick={onClose}>
                            {t('common.close', '关闭')}
                        </Button>
                        <Button onClick={fetchReleaseInfo} className="gap-2">
                            {t('common.retry', '重试')}
                        </Button>
                    </>
                );
        }
    };

    return (
        <Dialog
            isOpen={isOpen}
            onClose={state === 'downloading' || state === 'installing' ? () => {} : onClose}
            title={t('pluginInstall.title', '安装 PDF 翻译插件')}
        >
            {renderContent()}
            <DialogFooter>
                {renderFooter()}
            </DialogFooter>
        </Dialog>
    );
}
