import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogTitle,
} from "@/components/ui/dialog";
import { X, Copy, Share2, Link, Link2Off, Check } from "lucide-react";
import { toast } from "sonner";
import { getThread, updateProject, updateThread } from "@/lib/api";

interface SocialShareOption {
    name: string;
    icon: JSX.Element;
    onClick: () => void;
}

interface ShareModalProps {
    isOpen: boolean;
    onClose: () => void;
    threadId?: string;
    projectId?: string;
}

export function ShareModal({ isOpen, onClose, threadId, projectId }: ShareModalProps) {
    const [shareLink, setShareLink] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isChecking, setIsChecking] = useState(false);
    const [isCopying, setIsCopying] = useState(false);
    useEffect(() => {
        if (isOpen && threadId) {
            checkShareStatus();
        }
    }, [isOpen, threadId]);

    const checkShareStatus = async () => {
        if (!threadId) return;

        setIsChecking(true);

        try {
            const threadData = await getThread(threadId);

            if (threadData?.is_public) {
                const publicUrl = generateShareLink();
                setShareLink(publicUrl);
            } else {
                setShareLink(null);
            }
        } catch (error) {
            console.error("Error checking share status:", error);
            toast.error("Failed to check sharing status");
            setShareLink(null);
        } finally {
            setIsChecking(false);
        }
    };

    const generateShareLink = () => {
        if (!threadId) return "";
        return `${process.env.NEXT_PUBLIC_URL || window.location.origin}/share/${threadId}`;
    };

    const createShareLink = async () => {
        if (!threadId) return;

        setIsLoading(true);

        try {
            // Use the API to mark the thread as public
            await updatePublicStatus(true);
            const generatedLink = generateShareLink();
            setShareLink(generatedLink);
            toast.success("Shareable link created successfully");
        } catch (error) {
            console.error("Error creating share link:", error);
            toast.error("Failed to create shareable link");
        } finally {
            setIsLoading(false);
        }
    };

    const removeShareLink = async () => {
        if (!threadId) return;

        setIsLoading(true);

        try {
            // Use the API to mark the thread as private
            await updatePublicStatus(false);
            setShareLink(null);
            toast.success("Shareable link removed");
        } catch (error) {
            console.error("Error removing share link:", error);
            toast.error("Failed to remove shareable link");
        } finally {
            setIsLoading(false);
        }
    };

    const updatePublicStatus = async (isPublic: boolean) => {
        console.log("Updating public status for thread:", threadId, "and project:", projectId, "to", isPublic);
        if (!threadId) return;
        await updateProject(projectId, { is_public: isPublic });
        await updateThread(threadId, { is_public: isPublic });
    };

    const copyToClipboard = () => {
        if (shareLink) {
            setIsCopying(true);
            navigator.clipboard.writeText(shareLink);
            toast.success("Link copied to clipboard");
            setTimeout(() => {
                setIsCopying(false);
            }, 500);
        }
    };

    const socialOptions: SocialShareOption[] = [
        {
            name: "LinkedIn",
            icon: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="size-5 text-current">
                <path fill="currentColor" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
            </svg>,
            onClick: () => {
                if (shareLink) {
                    window.open(`https://www.linkedin.com/shareArticle?url=${encodeURIComponent(shareLink)}&text=Shared conversation`, '_blank');
                }
            }
        },
        {
            name: "X",
            icon: <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="size-5 text-current">
                <path fill="currentColor" d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z" />
            </svg>,
            onClick: () => {
                if (shareLink) {
                    window.open(`https://twitter.com/intent/tweet?url=${encodeURIComponent(shareLink)}&text=Shared conversation`, '_blank');
                }
            }
        }
    ];

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="sm:max-w-md p-0 gap-0 overflow-hidden">
                <DialogTitle className="p-4 font-medium">
                    Share Chat
                    <button
                        className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                        onClick={onClose}>
                        <X className="h-4 w-4" />
                        <span className="sr-only">Close</span>
                    </button>
                </DialogTitle>

                <div className="p-4 space-y-6">
                    {isChecking ? (
                        <div className="flex flex-col items-center justify-center py-10">
                            <div className="h-6 w-6 border-2 border-t-primary border-primary/30 rounded-full animate-spin"></div>
                            <p className="text-sm text-muted-foreground mt-4">Checking share status...</p>
                        </div>
                    ) : shareLink ? (
                        <>
                            <p className="text-sm text-muted-foreground">
                                Your chat is now publicly accessible with the link below. Anyone with this link can view this conversation.
                            </p>

                            <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-2">
                                <div className="relative flex flex-1 items-center">
                                    <input
                                        type="text"
                                        readOnly
                                        value={shareLink}
                                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                    />
                                </div>
                                <Button variant="outline" className="h-10 px-4 py-2" onClick={copyToClipboard}>
                                    {isCopying ? <Check className=" h-4 w-4" /> : <Copy className=" h-4 w-4" />}
                                </Button>
                            </div>

                            <div className="flex justify-center gap-6 pt-2">
                                {socialOptions.map((option, index) => (
                                    <button
                                        key={index}
                                        className="p-2 rounded-full flex flex-col items-center group"
                                        onClick={option.onClick}
                                    >
                                        <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-200">
                                            {option.icon}
                                        </div>
                                        <span className="text-xs mt-1 group-hover:text-primary transition-colors duration-200">{option.name}</span>
                                    </button>
                                ))}
                            </div>

                            <div className="pt-1">
                                <Button
                                    variant="default"
                                    className="w-full"
                                    onClick={removeShareLink}
                                    disabled={isLoading}
                                >
                                    <Link2Off className="mr-2 h-4 w-4" />
                                    {isLoading ? "Processing..." : "Remove link"}
                                </Button>
                            </div>
                        </>
                    ) : (
                        <>
                            <div className="flex flex-col items-center justify-center py-6 text-center">
                                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                    <Share2 className="h-6 w-6 text-primary" />
                                </div>
                                <h3 className="text-lg font-medium mb-2">Share this chat</h3>
                                <p className="text-sm text-muted-foreground max-w-sm mb-6">
                                    Create a shareable link that allows others to view this conversation.
                                </p>
                                <Button
                                    onClick={createShareLink}
                                    className="w-full max-w-xs"
                                    disabled={isLoading}
                                >
                                    <Link className="mr-2 h-4 w-4" />
                                    {isLoading ? "Creating link..." : "Create shareable link"}
                                </Button>
                            </div>
                        </>
                    )}
                </div>
            </DialogContent >
        </Dialog >
    );
}

