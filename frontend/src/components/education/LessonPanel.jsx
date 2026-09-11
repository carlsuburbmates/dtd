import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export default function LessonPanel({ eyebrow, title, tone = 'default', children }) {
  const isSoft = tone === 'soft';
  
  return (
    <Card className={`my-6 ${isSoft ? 'bg-muted/20 border-muted/30' : 'border-border'}`}>
      {(eyebrow || title) && (
        <CardHeader className="pb-3">
          {eyebrow && <span className="text-xs font-bold uppercase tracking-widest text-terracotta mb-1 block">{eyebrow}</span>}
          {title && <CardTitle className="text-xl font-serif">{title}</CardTitle>}
        </CardHeader>
      )}
      {children && (
        <CardContent className="pt-2 text-muted-foreground leading-relaxed">
          {children}
        </CardContent>
      )}
    </Card>
  );
}
