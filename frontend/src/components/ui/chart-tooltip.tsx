import React from "react"
import { cn } from "@/lib/utils"

const ChartTooltip = React.forwardRef(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-950 shadow-md dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50",
          className
        )}
        {...props}
      />
    )
  }
)
ChartTooltip.displayName = "ChartTooltip"

export { ChartTooltip }
