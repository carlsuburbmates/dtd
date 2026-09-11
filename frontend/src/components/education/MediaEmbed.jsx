import { useState } from 'react';
import VideoPlayer from './VideoPlayer';

export default function MediaEmbed({ src, caption, type = "video" }) {
  const [error, setError] = useState(false);

  return (
    <figure className='my-8 overflow-hidden rounded-xl border border-border/50 bg-muted/10 shadow-sm'>
      <div className='relative aspect-video bg-muted/30 flex items-center justify-center text-muted-foreground'>
        {error ? (
          <div className="flex flex-col items-center justify-center p-6 text-center">
            <span className="opacity-70 mb-2">Media generating...</span>
            <span className="text-xs opacity-50 font-mono">{src}</span>
          </div>
        ) : type === 'video' ? (
          <VideoPlayer 
            src={src} 
            poster="/images/mod_01_cover.jpg"
          />
        ) : (
          <img 
            src={src} 
            alt={caption || "Educational Media"} 
            className="w-full h-full object-cover"
            onError={() => setError(true)}
          />
        )}
      </div>
      {caption && (
        <figcaption className='p-4 text-sm text-muted-foreground border-t border-border/50 bg-background'>
          {caption}
        </figcaption>
      )}
    </figure>
  );
}
