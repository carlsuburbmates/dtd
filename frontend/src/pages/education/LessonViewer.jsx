import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Menu, X, CheckCircle2, ChevronRight, Lock, Volume2, Square } from 'lucide-react';
import confetti from 'canvas-confetti';
import { modules } from '@/data/modules';
import AuthWall from '@/components/AuthWall';
import VideoPlayer from '@/components/VideoPlayer';
const mdxModules = import.meta.glob('@/content/modules/**/*.mdx');

export default function LessonViewer() {
  const { moduleId, lessonId } = useParams();
  const navigate = useNavigate();
  const [MdxComponent, setMdxComponent] = useState(() => null);
  const [error, setError] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  const moduleIndex = modules.findIndex(m => m.id === moduleId);
  const moduleData = modules[moduleIndex];
  const lessonIndex = moduleData?.lessons.findIndex(l => l.id === lessonId);
  const lessonData = moduleData?.lessons[lessonIndex];

  // Dynamic Next Lesson Logic
  let nextModuleId = null;
  let nextLessonId = null;
  let nextLessonTitle = null;

  if (moduleData && lessonIndex !== undefined) {
    if (lessonIndex < moduleData.lessons.length - 1) {
      nextModuleId = moduleId;
      nextLessonId = moduleData.lessons[lessonIndex + 1].id;
      nextLessonTitle = moduleData.lessons[lessonIndex + 1].title;
    } else if (moduleIndex < modules.length - 1) {
      nextModuleId = modules[moduleIndex + 1].id;
      nextLessonId = modules[moduleIndex + 1].lessons[0].id;
      nextLessonTitle = modules[moduleIndex + 1].title + " - " + modules[moduleIndex + 1].lessons[0].title;
    }
  }

  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem('tfl_user'));
  const [progress, setProgress] = useState({});

  useEffect(() => {
    try {
      setProgress(JSON.parse(localStorage.getItem('tfl_progress') || '{}'));
    } catch (e) {}
  }, []);

  const isCompleted = progress[moduleId]?.includes(lessonId);

  const handleComplete = () => {
    try {
      const newProgress = { ...progress };
      if (!newProgress[moduleId]) newProgress[moduleId] = [];
      if (!newProgress[moduleId].includes(lessonId)) {
        newProgress[moduleId].push(lessonId);
      }
      localStorage.setItem('tfl_progress', JSON.stringify(newProgress));
      setProgress(newProgress);
      
      // Fire confetti!
      const end = Date.now() + 1000;
      const colors = ['#9B4F31', '#F5F2EB', '#5C6D59']; // terracotta, light, moss
      
      (function frame() {
        confetti({
          particleCount: 5,
          angle: 60,
          spread: 55,
          origin: { x: 0 },
          colors: colors
        });
        confetti({
          particleCount: 5,
          angle: 120,
          spread: 55,
          origin: { x: 1 },
          colors: colors
        });
      
        if (Date.now() < end) {
          requestAnimationFrame(frame);
        }
      }());

      // Dynamic Routing to next lesson instead of dashboard, with delay
      setTimeout(() => {
        if (nextModuleId && nextLessonId) {
          navigate(`/course/${nextModuleId}/${nextLessonId}`);
          window.scrollTo(0, 0);
        } else {
          navigate('/course');
        }
      }, 1200);
    } catch (e) {
      console.error("Failed to save progress", e);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadContent = async () => {
      const globPath = `/src/content/modules/${moduleId}/${lessonId}.mdx`;
      const importer = mdxModules[globPath];

      if (importer) {
        try {
          const mod = await importer();
          if (isMounted) {
            setMdxComponent(() => mod.default);
            setError(false);
          }
        } catch (e) {
          console.error("Failed to load MDX", e);
          if (isMounted) setError(true);
        }
      } else {
        if (isMounted) setError(true);
      }
    };

    loadContent();
    setIsSidebarOpen(false); // Close sidebar on navigation
    window.speechSynthesis.cancel();
    setIsPlayingAudio(false);
    return () => { 
      isMounted = false; 
      window.speechSynthesis.cancel();
    };
  }, [moduleId, lessonId]);

  if (!moduleData || !lessonData) {
    return <div className="p-12 text-center text-muted-foreground">Lesson not found.</div>;
  }

  const showWall = moduleData.isGated && !isAuthenticated;

  const SidebarContent = () => (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-border/40">
        <Link to="/course" className="text-sm font-medium text-muted-foreground hover:text-foreground flex items-center gap-2">
          &larr; Back to Dashboard
        </Link>
      </div>
      <div className="p-4 flex-1 overflow-y-auto">
        <h3 className="text-xs font-semibold tracking-widest text-muted-foreground uppercase mb-4">
          {moduleData.title}
        </h3>
        <nav className="flex flex-col gap-1">
          {moduleData.lessons.map((lesson) => {
            const isLessonCompleted = progress[moduleId]?.includes(lesson.id);
            const isActive = lesson.id === lessonId;
            return (
              <Link
                key={lesson.id}
                to={`/course/${moduleId}/${lesson.id}`}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                  isActive 
                    ? 'bg-terracotta/10 text-terracotta font-medium' 
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                }`}
              >
                {isLessonCompleted ? (
                  <CheckCircle2 className={`w-4 h-4 shrink-0 ${isActive ? 'text-terracotta' : 'text-terracotta/70'}`} />
                ) : (
                  <div className={`w-4 h-4 shrink-0 rounded-full border ${isActive ? 'border-terracotta' : 'border-muted-foreground/30'}`} />
                )}
                <span className="truncate">{lesson.title}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-background flex">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-72 border-r border-border/40 bg-muted/10 h-screen sticky top-0 shrink-0">
        <SidebarContent />
      </aside>

      {/* Mobile Drawer Overlay */}
      {isSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setIsSidebarOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-[80%] max-w-sm bg-background border-r border-border shadow-2xl">
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Sticky Mobile Header */}
        <header className="lg:hidden sticky top-0 z-40 bg-background/90 backdrop-blur-md border-b border-border/40 px-4 py-3 flex items-center justify-between shadow-sm">
          <button 
            onClick={() => setIsSidebarOpen(true)}
            className="p-1 -ml-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta rounded-sm flex items-center gap-2"
            aria-label="Open Course Menu"
          >
            <Menu className="w-5 h-5" />
            <span className="text-sm font-medium">Menu</span>
          </button>
          <span className="text-xs font-semibold tracking-widest text-muted-foreground uppercase truncate ml-4" aria-hidden="true">
            {moduleData.title}
          </span>
        </header>

        <main className="flex-1 relative">
          <div className={`max-w-3xl mx-auto px-6 py-12 md:py-16 pb-40 ${showWall ? 'h-[80vh] overflow-hidden relative' : ''}`}>
            
            {/* The MDX Content */}
            <article id="lesson-content-article" className={`prose prose-stone prose-lg max-w-[65ch] mx-auto prose-headings:font-serif prose-h1:text-4xl prose-h1:mb-8 prose-h2:mt-16 prose-h2:mb-6 prose-h2:text-3xl prose-h2:font-bold prose-h2:text-foreground prose-h3:mt-10 prose-h3:mb-4 prose-h3:text-xl prose-h3:font-semibold prose-h3:text-foreground prose-p:leading-relaxed prose-p:mb-6 prose-p:text-muted-foreground prose-strong:text-foreground prose-blockquote:border-l-4 prose-blockquote:border-terracotta prose-blockquote:bg-terracotta/5 prose-blockquote:py-4 prose-blockquote:px-6 prose-blockquote:rounded-r-xl prose-blockquote:not-italic prose-blockquote:font-normal prose-blockquote:text-foreground prose-li:marker:text-terracotta prose-a:text-terracotta hover:prose-a:text-terracotta-deep ${showWall ? '[mask-image:linear-gradient(to_bottom,black_10%,transparent_60%)] select-none pointer-events-none' : ''}`}>
              <h1 className="editorial-h1 text-4xl md:text-5xl mb-8">{lessonData.title}</h1>
              
              {!showWall && !error && (
                <div className="flex items-center gap-4 mb-12 not-prose">
                  <button
                    onClick={() => {
                      if (isPlayingAudio) {
                        window.speechSynthesis.cancel();
                        setIsPlayingAudio(false);
                      } else {
                        const text = document.getElementById('lesson-content-article')?.innerText;
                        if (text) {
                          const utterance = new SpeechSynthesisUtterance(text);
                          // Try to find a good voice
                          const voices = window.speechSynthesis.getVoices();
                          const preferredVoice = voices.find(v => v.name.includes('Samantha') || v.name.includes('Google US English'));
                          if (preferredVoice) utterance.voice = preferredVoice;
                          
                          utterance.rate = 0.95;
                          utterance.pitch = 1;
                          utterance.onend = () => setIsPlayingAudio(false);
                          
                          setIsPlayingAudio(true);
                          window.speechSynthesis.speak(utterance);
                        }
                      }
                    }}
                    className="flex items-center gap-2 bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground px-4 py-2 rounded-full text-sm font-medium transition-colors border border-border"
                  >
                    {isPlayingAudio ? (
                      <>
                        <Square className="w-4 h-4 fill-current text-terracotta" />
                        Stop Listening
                      </>
                    ) : (
                      <>
                        <Volume2 className="w-4 h-4 text-terracotta" />
                        Listen to Lesson
                      </>
                    )}
                  </button>
                </div>
              )}

              {error ? (
                <p className="text-destructive">Failed to load lesson content. The file might be missing.</p>
              ) : MdxComponent ? (
                <MdxComponent components={{ video: (props) => <VideoPlayer {...props} /> }} />
              ) : (
                <p className="text-muted-foreground">Loading...</p>
              )}
            </article>

            {/* Blurred Teaser Overlay for Gated Content */}
            {showWall && (
              <div className="absolute inset-0 z-10 flex items-center justify-center pt-32 px-4">
                <div className="w-full max-w-md pointer-events-auto shadow-2xl">
                  <AuthWall onSuccess={() => setIsAuthenticated(true)} />
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Sticky Action Bar (Thumb Zone) */}
        {!showWall && !error && (
          <nav className="fixed bottom-0 left-0 lg:left-72 right-0 bg-background/95 backdrop-blur-md border-t border-border/40 p-4 pb-[max(1rem,env(safe-area-inset-bottom))] z-30 shadow-[0_-8px_16px_rgba(0,0,0,0.02)]" aria-label="Lesson actions">
            <div className="max-w-3xl mx-auto flex flex-col sm:flex-row gap-4 items-center">
              <button 
                onClick={handleComplete}
                className={`w-full sm:w-auto flex-1 py-4 px-6 text-lg font-medium shadow-sm transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terracotta focus-visible:ring-offset-2 min-h-[56px] rounded-xl flex items-center justify-center gap-2 ${
                  isCompleted 
                  ? "bg-muted text-foreground border border-border" 
                  : "bg-terracotta text-white hover:bg-terracotta-deep"
                }`}
                aria-pressed={isCompleted}
              >
                {isCompleted ? (
                  <>
                    <CheckCircle2 className="w-5 h-5 text-terracotta" />
                    Completed
                  </>
                ) : (
                  "Complete & Continue"
                )}
              </button>
              
              {/* Up Next Teaser */}
              {nextLessonTitle && (
                <div className="hidden sm:flex flex-col flex-1 pl-4 border-l border-border/50 text-left">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Up Next</span>
                  <span className="text-sm font-medium text-foreground truncate">{nextLessonTitle}</span>
                </div>
              )}
            </div>
          </nav>
        )}
      </div>
    </div>
  );
}
