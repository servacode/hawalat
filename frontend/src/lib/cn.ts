/** دمج أصناف Tailwind بشكل آمن — أداة مركزية بسيطة بلا اعتماديات. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
