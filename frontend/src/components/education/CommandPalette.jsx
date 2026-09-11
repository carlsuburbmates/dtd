import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Command } from 'cmdk';
import { Search } from 'lucide-react';
import { modules } from '@/data/modules';

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  // Toggle the menu when ⌘K is pressed
  useEffect(() => {
    const down = (e) => {
      if (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="Global Command Menu"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] sm:pt-[20vh]"
    >
      <div 
        className="fixed inset-0 bg-background/80 backdrop-blur-sm -z-10" 
        onClick={() => setOpen(false)} 
      />
      <div className="w-[90vw] max-w-2xl bg-card border border-border rounded-xl shadow-2xl overflow-hidden text-card-foreground">
        <div className="flex items-center border-b border-border px-4 py-3 gap-3">
          <Search className="w-5 h-5 text-muted-foreground" />
          <Command.Input 
            placeholder="Search for lessons, topics... (Try 'Leash' or 'Puppy')" 
            className="flex-1 bg-transparent border-none outline-none text-base placeholder:text-muted-foreground focus:ring-0 h-10" 
          />
        </div>
        <Command.List className="max-h-[60vh] overflow-y-auto p-2 scrollbar-thin">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            No lessons found.
          </Command.Empty>
          
          {modules.map((module) => (
            <Command.Group key={module.id} heading={module.title} className="text-xs font-semibold tracking-widest text-muted-foreground uppercase px-2 py-3 [&_[cmdk-group-heading]]:mb-2 [&_[cmdk-group-heading]]:px-1">
              {module.lessons.map((lesson) => (
                <Command.Item
                  key={lesson.id}
                  value={`${module.title} ${lesson.title}`}
                  onSelect={() => {
                    navigate(`/the-first-leash/modules/${module.id}/lessons/${lesson.id}`);
                    setOpen(false);
                  }}
                  className="flex items-center gap-3 px-3 py-3 rounded-md text-sm text-foreground hover:bg-terracotta/10 hover:text-terracotta cursor-pointer transition-colors data-[selected=true]:bg-terracotta/10 data-[selected=true]:text-terracotta outline-none"
                >
                  <span className="font-medium text-base normal-case tracking-normal">{lesson.title}</span>
                </Command.Item>
              ))}
            </Command.Group>
          ))}
        </Command.List>
      </div>
    </Command.Dialog>
  );
}
