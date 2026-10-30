import { cva, type VariantProps } from "class-variance-authority"
import * as React from "react"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em]",
  {
    variants: {
      variant: {
        default: "border-rule bg-paper-deep text-muted",
        stamp: "border-stamp/30 bg-stamp/10 text-stamp",
        grove: "border-grove/20 bg-grove-soft text-grove",
        amber: "border-amber/40 bg-amber/15 text-ink",
      },
    },
    defaultVariants: { variant: "default" },
  },
)

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
