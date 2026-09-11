import React from 'react';
import Plyr from 'plyr-react';
import 'plyr-react/plyr.css';

export default function VideoPlayer({ src, poster }) {
  const plyrProps = {
    source: {
      type: 'video',
      sources: [
        {
          src: src,
          type: 'video/mp4',
        },
      ],
      poster: poster,
    },
    options: {
      controls: ['play-large', 'play', 'progress', 'current-time', 'mute', 'volume', 'fullscreen'],
      hideControls: true,
    }
  };

  return (
    <div className="w-full rounded-2xl overflow-hidden shadow-lg border border-border/50 my-10 plyr-theme-override isolate">
      <Plyr {...plyrProps} />
    </div>
  );
}
