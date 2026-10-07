import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

export const buttonStyles = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-ctl)] font-medium transition-[background-color,border-color,color,transform] duration-150 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        primary: "bg-ink text-bg hover:bg-ink-soft",
        accent: "bg-accent text-on-accent hover:bg-accent-hover",
        secondary: "border border-line-strong bg-surface text-ink hover:bg-sunken",
        ghost: "text-ink-soft hover:bg-sunken hover:text-ink",
        danger: "border border-line-strong bg-surface text-error hover:bg-error-soft",
      },
      size: {
        sm: "h-8 px-3 text-[13px]",
        md: "h-9 px-3.5 text-[13.5px]",
        lg: "h-11 px-5 text-[15px]",
        icon: "h-8 w-8 text-[13px]",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export function Button({
  className,
  variant,
  size,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof buttonStyles>) {
  return <button className={cn(buttonStyles({ variant, size }), className)} {...props} />;
}
