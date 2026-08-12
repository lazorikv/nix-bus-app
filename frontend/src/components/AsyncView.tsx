import type { ReactNode } from "react";

interface AsyncViewProps {
  loading: boolean;
  error: string | null;
  isEmpty?: boolean;
  emptyMessage?: string;
  onRetry?: () => void;
  children: ReactNode;
}

/** Standard loading / error / empty scaffolding for any async view. */
export function AsyncView({
  loading,
  error,
  isEmpty,
  emptyMessage = "Nothing here yet.",
  onRetry,
  children,
}: AsyncViewProps) {
  if (loading) {
    return (
      <div className="state state--loading" role="status">
        <span className="spinner" aria-hidden /> Loading…
      </div>
    );
  }
  if (error) {
    return (
      <div className="state state--error" role="alert">
        <p>{error}</p>
        {onRetry && (
          <button className="btn btn--sm" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  }
  if (isEmpty) {
    return <div className="state state--empty">{emptyMessage}</div>;
  }
  return <>{children}</>;
}
