export function LoadingState({ message = "Loading..." }: { message?: string }) {
  return <div className="state-card" aria-live="polite">{message}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="state-card state-card--error" role="alert">{message}</div>;
}

export function EmptyState({ message }: { message: string }) {
  return <div className="state-card">{message}</div>;
}
