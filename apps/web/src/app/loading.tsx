export default function Loading() {
  return (
    <div className="shell py-16">
      <div className="h-3 w-32 animate-pulse rounded bg-paper-deep" />
      <div className="mt-5 h-14 w-2/3 animate-pulse rounded bg-paper-deep" />
      <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-paper-deep" />
      <div className="mt-10 grid gap-4 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-64 animate-pulse border border-line bg-paper-raised/60" />
        ))}
      </div>
    </div>
  );
}
