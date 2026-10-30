import * as React from "react"

import { cn } from "@/lib/utils"

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "flex min-h-24 w-full rounded-sm border border-rule bg-paper px-3 py-2 text-sm text-ink shadow-none placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-stamp disabled:opacity-50",
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
