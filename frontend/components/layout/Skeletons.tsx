/** Placeholder shapes shown while data loads, so the layout never jumps. */

function Block({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-skeleton ${className}`} />;
}

export function ChatSkeleton() {
  return (
    <div role="status" aria-label="Loading conversation" className="flex flex-1 flex-col gap-5 px-4 py-5 sm:px-5">
      <span className="sr-only">Loading conversation…</span>
      <div className="flex justify-end">
        <Block className="h-9 w-48 rounded-2xl rounded-br-md" />
      </div>
      <div className="flex flex-col gap-2">
        <Block className="h-4 w-[78%]" />
        <Block className="h-4 w-[64%]" />
        <Block className="h-4 w-[42%]" />
      </div>
      <div className="flex justify-end">
        <Block className="h-9 w-36 rounded-2xl rounded-br-md" />
      </div>
      <div className="flex flex-col gap-2">
        <Block className="h-4 w-[70%]" />
        <Block className="h-4 w-[52%]" />
      </div>
    </div>
  );
}

export function OutputSkeleton() {
  return (
    <div role="status" aria-label="Loading results" className="flex flex-col gap-6">
      <span className="sr-only">Loading results…</span>
      <div className="flex flex-col gap-2.5">
        <Block className="h-3 w-16" />
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-2.5">
            <Block className="size-4 rounded-full" />
            <Block className="h-3.5 w-44" />
          </div>
        ))}
      </div>
      <Block className="h-64 w-full rounded-xl" />
      <div className="flex flex-col gap-2">
        <Block className="h-3 w-12" />
        <Block className="h-9 w-full" />
        <Block className="h-9 w-full" />
        <Block className="h-9 w-full" />
      </div>
    </div>
  );
}

/** The whole app shell, shown while the session is being checked. */
export function AppSkeleton() {
  return (
    <main role="status" aria-label="Loading your workspace" className="flex h-dvh flex-col">
      <span className="sr-only">Loading your workspace…</span>
      <div className="flex items-center justify-between gap-4 border-b border-line bg-panel px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <Block className="size-8 rounded-md" />
          <div className="flex flex-col gap-1.5">
            <Block className="h-4 w-56" />
            <Block className="h-3 w-32" />
          </div>
        </div>
        <div className="flex gap-2">
          <Block className="size-9 rounded-lg" />
          <Block className="h-9 w-20 rounded-lg" />
        </div>
      </div>
      <div className="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_minmax(0,1fr)] lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:grid-rows-1">
        <div className="flex flex-col border-b border-line bg-canvas lg:border-r lg:border-b-0">
          <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
            <Block className="h-7 w-40 rounded-lg" />
            <Block className="h-7 w-20 rounded-lg" />
          </div>
          <div className="flex-1" />
          <div className="border-t border-line bg-panel px-4 py-3">
            <Block className="h-12 w-full rounded-lg" />
          </div>
        </div>
        <div className="bg-panel p-4 sm:p-6">
          <Block className="h-64 w-full rounded-xl" />
        </div>
      </div>
    </main>
  );
}
