import { CheckCircle2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';

export default function ChecklistBlock({ title, subtitle, items = [], variant = 'checklist' }) {
  const isWorksheet = variant === 'worksheet';
  
  return (
    <Card className={`my-6 ${isWorksheet ? 'border-terracotta/20 bg-terracotta/5' : 'bg-muted/30 border-muted'}`}>
      {(title || subtitle) && (
        <CardHeader className="pb-3">
          {title && <CardTitle className="text-xl font-serif">{title}</CardTitle>}
          {subtitle && <CardDescription className="text-base text-muted-foreground">{subtitle}</CardDescription>}
        </CardHeader>
      )}
      <CardContent className={!title && !subtitle ? "pt-6" : ""}>
        <ul className="space-y-3">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-3 text-foreground">
              <CheckCircle2 className={`w-5 h-5 shrink-0 mt-0.5 ${isWorksheet ? 'text-terracotta' : 'text-muted-foreground'}`} />
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
