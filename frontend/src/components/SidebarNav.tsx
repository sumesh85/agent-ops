"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function NavItem({
  href, icon, label, disabled,
}: {
  href: string; icon: string; label: string; disabled?: boolean;
}) {
  const pathname = usePathname();
  const active = !disabled && pathname === href;

  const base = "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors";
  const cls = disabled
    ? `${base} text-slate-600 cursor-not-allowed`
    : active
      ? `${base} bg-slate-800 text-slate-100 font-medium`
      : `${base} text-slate-400 hover:bg-slate-800/60 hover:text-slate-200`;

  if (disabled) {
    return (
      <span className={cls}>
        <span className="text-base">{icon}</span>
        {label}
      </span>
    );
  }

  return (
    <Link href={href} className={cls}>
      <span className="text-base">{icon}</span>
      {label}
    </Link>
  );
}

export default function SidebarNav() {
  return (
    <nav className="flex-1 p-3 space-y-0.5">
      <NavItem href="/overview"    icon="📈" label="Overview" />
      <NavItem href="/issues"      icon="📋" label="Issues" />
      <NavItem href="/escalations" icon="🚨" label="Escalations" />
      <NavItem href="/analytics"   icon="📊" label="Analytics" />
      <NavItem href="#"            icon="🔁" label="Replay"    disabled />
    </nav>
  );
}
