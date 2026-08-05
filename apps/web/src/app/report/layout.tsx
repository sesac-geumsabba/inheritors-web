export default function ReportLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="prototype-shell min-h-[max(884px,100dvh)] bg-background font-body-md text-on-background antialiased">
      {children}
    </div>
  );
}
