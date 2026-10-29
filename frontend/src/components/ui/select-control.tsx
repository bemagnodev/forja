import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './select';
import { cn } from '@/lib/utils';

interface Props {
  label: string;
  value: string;
  options: readonly { value: string; label: string }[];
  onValueChange: (value: string) => void;
  className?: string;
}

export function SelectControl({ label, value, options, onValueChange, className }: Props) {
  return <Select value={value} items={options} onValueChange={next => { if (next !== null) onValueChange(next); }}>
    <SelectTrigger aria-label={label} className={cn('max-w-full', className)}><SelectValue /></SelectTrigger>
    <SelectContent align="start" alignItemWithTrigger={false}>
      {options.map(option => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
    </SelectContent>
  </Select>;
}
