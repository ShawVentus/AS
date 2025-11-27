import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            return this.props.fallback || (
                <div className="p-6 bg-red-950/50 border border-red-500/30 rounded-xl text-red-200 m-4">
                    <h2 className="text-lg font-bold mb-2 flex items-center gap-2">
                        <span>⚠️</span>
                        Something went wrong
                    </h2>
                    <p className="text-sm text-red-300/80 mb-4">
                        The application encountered an error while rendering this section.
                    </p>
                    <div className="bg-black/30 p-3 rounded text-xs font-mono text-red-300 overflow-auto max-h-32">
                        {this.state.error?.message}
                    </div>
                    <button
                        onClick={() => this.setState({ hasError: false, error: null })}
                        className="mt-4 px-4 py-2 bg-red-900/50 hover:bg-red-800/50 text-red-100 rounded-lg text-sm transition-colors"
                    >
                        Try again
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}
