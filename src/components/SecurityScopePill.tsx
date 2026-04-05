export function SecurityScopePill({ scope }: { scope: string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-muted text-xs font-mono text-muted-foreground border border-border">
      {scope}
    </span>
  );
}
