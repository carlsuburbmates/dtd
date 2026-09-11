import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Lock, ArrowRight, PlayCircle, CheckCircle2, Play } from 'lucide-react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { modules } from '@/data/modules';

export default function CourseDashboard() {
  const [isAuthenticated] = useState(() => !!localStorage.getItem('tfl_user'));
  const [progress, setProgress] = useState({});

  useEffect(() => {
    try {
      setProgress(JSON.parse(localStorage.getItem('tfl_progress') || '{}'));
    } catch (e) {}
  }, []);

  // Calculate the "Next Incomplete" lesson
  let nextToResume = null;
  
  // Only attempt to find next if they've started something
  const hasStarted = Object.keys(progress).length > 0;
  
  if (hasStarted) {
    for (const module of modules) {
      const completedIds = progress[module.id] || [];
      const firstIncomplete = module.lessons.find(l => !completedIds.includes(l.id));
      
      if (firstIncomplete) {
        // We only want to recommend it if it's NOT gated or if they are authenticated
        if (!module.isGated || isAuthenticated) {
          nextToResume = {
            module,
            lesson: firstIncomplete
          };
          break; // Stop at the very first incomplete one they can access
        }
      }
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-6 md:p-12 pb-32">
      <header className="mb-12 flex items-center justify-between">
        <div>
          <h1 className="editorial-h1 text-5xl mb-4">The First Leash</h1>
          <p className="text-xl text-muted-foreground">Select a module to continue your training journey.</p>
        </div>
        <button 
          onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
          className="hidden md:flex items-center gap-2 px-4 py-2 bg-muted/30 hover:bg-muted text-muted-foreground rounded-full border border-border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta"
          aria-label="Search Course"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <span className="text-sm font-medium">Search</span>
          <kbd className="ml-2 pointer-events-none inline-flex h-5 items-center gap-1 rounded border border-border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
            <span className="text-xs">⌘</span>K
          </kbd>
        </button>
      </header>

      {/* Hero: Resume Journey */}
      {nextToResume && (
        <div className="mb-12">
          <div className="bg-terracotta/5 border border-terracotta/20 rounded-2xl p-6 md:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-terracotta/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
            <div className="relative z-10">
              <span className="text-xs font-bold uppercase tracking-widest text-terracotta mb-2 block">Pick up where you left off</span>
              <h2 className="text-2xl md:text-3xl font-serif font-medium text-foreground mb-2">
                {nextToResume.module.title}
              </h2>
              <p className="text-muted-foreground">
                Up next: <span className="font-medium text-foreground">{nextToResume.lesson.title}</span>
              </p>
            </div>
            <Link 
              to={`/the-first-leash/modules/${nextToResume.module.id}/lessons/${nextToResume.lesson.id}`}
              className="relative z-10 shrink-0 bg-terracotta text-white hover:bg-terracotta-deep px-6 py-3 rounded-lg font-medium transition-colors flex items-center shadow-sm"
            >
              Resume Lesson <Play className="w-4 h-4 ml-2 fill-current" />
            </Link>
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {modules.map((module, index) => {
          const isLocked = module.isGated && !isAuthenticated;
          const completedCount = progress[module.id]?.length || 0;
          const totalLessons = module.lessons.length;
          const percent = totalLessons > 0 ? Math.round((completedCount / totalLessons) * 100) : 0;
          const isCompleted = completedCount === totalLessons && totalLessons > 0;
          const imageId = module.id.split('-')[0];
          
          return (
            <motion.div 
              key={module.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              <Card className={`group relative overflow-hidden h-full flex flex-col transition-all duration-500 hover:shadow-xl hover:-translate-y-1 ${isLocked ? "opacity-90 bg-muted/20" : "bg-card hover:border-terracotta/50"}`}>
                
                {/* Background Puppy Image */}
                <div className="absolute inset-0 z-0 pointer-events-none">
                  <img 
                    src={`/images/mod_${imageId}_puppy.jpg`}
                    alt={`Puppy for ${module.title}`}
                    className="absolute inset-0 w-full h-full object-cover scale-105 group-hover:scale-100 opacity-0 group-hover:opacity-100 transition-all duration-700 ease-out z-0"
                  />
                  {/* Strong black gradient so white text is highly readable on hover */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/60 to-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-500 z-10" />
                </div>

                <div className="relative z-20 flex flex-col h-full">
                  <CardHeader className="group-hover:text-white transition-colors duration-300">
                    <div className="flex justify-between items-start">
                      <CardTitle className="flex items-center gap-2 group-hover:text-white">
                        {module.title}
                        {isCompleted && <CheckCircle2 className="w-5 h-5 text-terracotta group-hover:text-white/90" />}
                      </CardTitle>
                      {isLocked && <Lock className="w-5 h-5 text-muted-foreground group-hover:text-white/70" aria-label="Locked module" />}
                    </div>
                    <CardDescription className="text-base mt-2 group-hover:text-white/80 transition-colors duration-300">
                      {module.description}
                    </CardDescription>
                    
                    <div className="mt-6 flex flex-col gap-2">
                      <div className="flex justify-between items-center text-sm font-medium">
                        <span className="text-muted-foreground group-hover:text-white/80 transition-colors duration-300">{completedCount} of {totalLessons} Lessons</span>
                        <span className="text-terracotta group-hover:text-white transition-colors duration-300">{percent}%</span>
                      </div>
                      <div className="h-2 w-full bg-muted/50 group-hover:bg-white/20 rounded-full overflow-hidden transition-colors duration-300" role="progressbar" aria-valuenow={percent} aria-valuemin="0" aria-valuemax="100">
                        <div 
                          className="h-full bg-terracotta group-hover:bg-white transition-all duration-500 ease-out" 
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  </CardHeader>
                  <CardFooter className="mt-auto">
                    {isLocked ? (
                      <Link to={`/the-first-leash/modules/${module.id}/lessons/${module.lessons[0].id}`} className="btn-ghost px-0 text-muted-foreground group-hover:text-white/80 hover:bg-transparent transition-colors duration-300 relative z-30">
                        Unlock Module <Lock className="w-4 h-4 ml-1" />
                      </Link>
                    ) : (
                      <Link to={`/the-first-leash/modules/${module.id}/lessons/${module.lessons[0].id}`} className="btn-ghost px-0 text-terracotta group-hover:text-white hover:text-terracotta-deep group-hover:hover:text-white/80 hover:bg-transparent transition-colors duration-300 relative z-30">
                        Start Learning <PlayCircle className="w-4 h-4 ml-2 group-hover:scale-110 transition-transform" />
                      </Link>
                    )}
                  </CardFooter>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
