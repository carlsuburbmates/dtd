import { useState } from 'react';
import { Input } from './ui/Input';
import { Button } from './ui/Button';

export default function AuthWall({ onSuccess }) {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email) {
      localStorage.setItem('tfl_user', email);
      setSubmitted(true);
      setTimeout(() => {
        onSuccess();
      }, 1500);
    }
  };

  return (
    <div className="card-public max-w-lg mx-auto p-8 text-center mt-12 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-terracotta/5 to-moss/5 pointer-events-none" />
      
      {submitted ? (
        <div className="relative z-10 py-8">
          <div className="w-16 h-16 bg-moss/10 text-moss rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="editorial-h2 text-3xl mb-2">Welcome Back</h2>
          <p className="text-muted-foreground">Unlocking your next module...</p>
        </div>
      ) : (
        <div className="relative z-10">
          <h2 className="editorial-h2 text-3xl mb-4">Unlock the Full Course</h2>
          <p className="text-muted-foreground mb-8">
            You've completed the fundamentals. Enter your email to get free access to the remaining modules and exclusive training tips.
          </p>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input 
              type="email" 
              placeholder="Enter your email address" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="text-center"
            />
            <Button type="submit" size="lg" className="w-full">
              Unlock Full Access
            </Button>
          </form>
          <p className="text-xs text-muted-foreground mt-6 uppercase tracking-widest font-mono">
            100% Free. No spam.
          </p>
        </div>
      )}
    </div>
  );
}
