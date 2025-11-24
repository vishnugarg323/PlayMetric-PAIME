import { Brain, Upload, Play, Database, Eye, Zap, Code2, Globe, Shield, Smartphone, Rocket, TrendingUp, Mail, Phone, MapPin, Send } from 'lucide-react'
import { useState, useEffect } from 'react'

export default function About() {
  const [demoVideoUrl, setDemoVideoUrl] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/system/demo-video')
      .then(r => r.json())
      .then(data => {
        if (data.video_url) {
          setDemoVideoUrl(data.video_url)
        }
      })
      .catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-purple-950 overflow-hidden">
      
      {/* Hero Section with Floating Phones */}
      <div className="relative min-h-screen flex items-center justify-center px-4 py-20 overflow-hidden">
        {/* Animated Background Orbs with Glow */}
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl animate-pulse-glow"></div>
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse-glow" style={{animationDelay: '1s'}}></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-pink-500/10 rounded-full blur-3xl animate-pulse-glow" style={{animationDelay: '2s'}}></div>
        
        {/* Matrix Rain Effect Particles */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          {[...Array(20)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1 bg-gradient-to-b from-cyan-500 via-blue-500 to-transparent opacity-30 animate-matrix-rain"
              style={{
                left: `${(i * 5) % 100}%`,
                height: `${Math.random() * 100 + 50}px`,
                animationDelay: `${Math.random() * 3}s`,
                animationDuration: `${Math.random() * 2 + 3}s`
              }}
            />
          ))}
        </div>
        
        {/* Glitch Effect Overlay */}
        <div className="absolute inset-0 pointer-events-none opacity-0 hover:opacity-100 transition-opacity duration-1000">
          <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-transparent to-purple-500/10 animate-glitch"></div>
        </div>
        
        {/* Floating Particles */}
        <div className="absolute top-1/4 left-1/3 w-2 h-2 bg-blue-400 rounded-full animate-float-slow glow-blue"></div>
        <div className="absolute top-1/3 right-1/4 w-3 h-3 bg-purple-400 rounded-full animate-float-slower glow-purple"></div>
        <div className="absolute bottom-1/3 left-1/4 w-2 h-2 bg-pink-400 rounded-full animate-float-slow glow-pink" style={{animationDelay: '1s'}}></div>
        <div className="absolute top-2/3 right-1/3 w-2 h-2 bg-green-400 rounded-full animate-float-slower glow-green" style={{animationDelay: '2s'}}></div>
        
        {/* Detailed Mobile Phones with Screens */}
        {/* Phone 1 - Top Left */}
        <div className="absolute top-20 left-20 phone-float phone-3d" style={{animationDelay: '0s'}}>
          <div className="w-36 h-72 bg-gradient-to-br from-slate-900 to-slate-800 rounded-[2.5rem] shadow-2xl border-4 border-slate-700 relative transform hover:scale-110 transition-all duration-500 phone-glow-blue">
            {/* Notch */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-20 h-6 bg-slate-900 rounded-b-3xl z-10"></div>
            {/* Screen with Holographic Effect */}
            <div className="absolute inset-3 top-8 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-3xl overflow-hidden holographic-effect">
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent"></div>
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent animate-shimmer"></div>
              {/* App Icons */}
              <div className="grid grid-cols-3 gap-2 p-3 mt-4">
                <div className="w-8 h-8 bg-white/20 backdrop-blur rounded-xl animate-pulse-icon"></div>
                <div className="w-8 h-8 bg-white/20 backdrop-blur rounded-xl animate-pulse-icon" style={{animationDelay: '0.2s'}}></div>
                <div className="w-8 h-8 bg-white/20 backdrop-blur rounded-xl animate-pulse-icon" style={{animationDelay: '0.4s'}}></div>
              </div>
            </div>
            {/* Power Button */}
            <div className="absolute right-0 top-20 w-1 h-12 bg-slate-600 rounded-l"></div>
          </div>
        </div>
        
        {/* Phone 2 - Bottom Right */}
        <div className="absolute bottom-32 right-20 phone-float phone-3d" style={{animationDelay: '1.5s'}}>
          <div className="w-40 h-80 bg-gradient-to-br from-slate-900 to-slate-800 rounded-[3rem] shadow-2xl border-4 border-slate-700 relative transform hover:scale-110 transition-all duration-500 phone-glow-green">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-7 bg-slate-900 rounded-b-3xl z-10"></div>
            <div className="absolute inset-3 top-9 bg-gradient-to-br from-green-500 via-teal-500 to-cyan-500 rounded-[2rem] overflow-hidden holographic-effect">
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent"></div>
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent animate-shimmer"></div>
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 w-12 h-1 bg-white/30 rounded-full animate-pulse"></div>
            </div>
            <div className="absolute right-0 top-24 w-1 h-16 bg-slate-600 rounded-l"></div>
          </div>
        </div>

        {/* Phone 3 - Top Right - Gaming */}
        <div className="absolute top-32 right-32 phone-float phone-3d" style={{animationDelay: '0.7s'}}>
          <div className="w-32 h-64 bg-gradient-to-br from-slate-900 to-slate-800 rounded-[2rem] shadow-2xl border-4 border-slate-700 relative transform hover:scale-110 transition-all duration-500 phone-glow-orange">
            <div className="absolute inset-2 top-6 bg-gradient-to-br from-orange-500 via-red-500 to-pink-500 rounded-2xl overflow-hidden holographic-effect">
              <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent animate-shimmer"></div>
              {/* Game UI */}
              <div className="absolute top-2 left-2 right-2 flex justify-between">
                <div className="w-8 h-8 bg-white/20 backdrop-blur rounded-lg animate-pulse-icon"></div>
                <div className="w-16 h-6 bg-white/20 backdrop-blur rounded-full animate-pulse"></div>
              </div>
            </div>
          </div>
        </div>

        {/* Phone 4 - Bottom Left - Testing */}
        <div className="absolute bottom-40 left-32 phone-float phone-3d" style={{animationDelay: '2s'}}>
          <div className="w-28 h-56 bg-gradient-to-br from-slate-900 to-slate-800 rounded-[2rem] shadow-2xl border-4 border-slate-700 relative transform hover:scale-110 transition-all duration-500 phone-glow-purple">
            <div className="absolute inset-2 top-5 bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 rounded-xl overflow-hidden holographic-effect">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.1),transparent)]"></div>
              <div className="absolute inset-0 bg-gradient-to-br from-white/20 via-transparent to-transparent animate-shimmer"></div>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-12 h-12 border-4 border-white/50 rounded-full animate-spin-slow neon-ring-small"></div>
            </div>
          </div>
        </div>
        
        {/* Neon Rings */}
        <div className="absolute top-1/3 left-1/2 w-64 h-64 border-2 border-cyan-500/30 rounded-full animate-spin-very-slow neon-ring"></div>
        <div className="absolute bottom-1/3 right-1/4 w-48 h-48 border-2 border-purple-500/30 rounded-full animate-spin-slow-reverse neon-ring"></div>

        {/* Center Content */}
        <div className="relative z-10 text-center max-w-6xl mx-auto px-6">
          <img 
            src="/logo.png" 
            alt="PlayMetric Logo" 
            className="w-24 h-24 md:w-32 md:h-32 mx-auto mb-8 animate-float drop-shadow-2xl logo-glow"
            style={{
              filter: 'drop-shadow(0 0 30px rgba(147,51,234,0.5))',
              transform: `translateY(${Math.sin(scrollY * 0.01) * 10}px)`
            }}
          />
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 animate-gradient leading-tight neon-text">
            PlayMetric PAIME
          </h1>
          <div className="relative inline-block mb-6">
            <p className="text-xl md:text-2xl lg:text-3xl text-slate-200 font-medium glitch-text" data-text="AI-Powered Autonomous Mobile Game Testing">
              AI-Powered Autonomous Mobile Game Testing
            </p>
          </div>
          <p className="text-base md:text-lg text-slate-300 mb-10 max-w-3xl mx-auto leading-relaxed animate-fade-in-up">
            Transform your QA process with cutting-edge AI that learns, tests, and reports bugs autonomously—24/7, no human intervention required.
          </p>

          {/* Stats Badges */}
          <div className="flex flex-wrap justify-center gap-3 md:gap-4 mb-16">
            <div className="px-5 md:px-6 py-2.5 md:py-3 bg-blue-500/10 backdrop-blur-lg rounded-full border border-blue-400/20 hover:bg-blue-500/20 hover:border-blue-400/40 transition-all duration-300 shadow-lg shadow-blue-500/10 badge-glow-blue hover:scale-110 group">
              <span className="text-sm md:text-base text-blue-200 font-semibold group-hover:text-blue-100">⚡ 24/7 Automated</span>
            </div>
            <div className="px-5 md:px-6 py-2.5 md:py-3 bg-purple-500/10 backdrop-blur-lg rounded-full border border-purple-400/20 hover:bg-purple-500/20 hover:border-purple-400/40 transition-all duration-300 shadow-lg shadow-purple-500/10 badge-glow-purple hover:scale-110 group">
              <span className="text-sm md:text-base text-purple-200 font-semibold group-hover:text-purple-100">🤖 100% AI-Driven</span>
            </div>
            <div className="px-5 md:px-6 py-2.5 md:py-3 bg-pink-500/10 backdrop-blur-lg rounded-full border border-pink-400/20 hover:bg-pink-500/20 hover:border-pink-400/40 transition-all duration-300 shadow-lg shadow-pink-500/10 badge-glow-pink hover:scale-110 group">
              <span className="text-sm md:text-base text-pink-200 font-semibold group-hover:text-pink-100">🚀 10x Faster QA</span>
            </div>
          </div>
          
          {/* Scroll Indicator */}
          <div className="mt-20">
            <div className="animate-bounce">
              <div className="w-6 h-10 border-2 border-slate-400/50 rounded-full p-1 mx-auto backdrop-blur neon-border">
                <div className="w-1.5 h-3 bg-gradient-to-b from-blue-400 to-purple-400 rounded-full mx-auto animate-pulse glow-blue"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Game Genre Showcase */}
      <div className="relative py-20 px-4 overflow-hidden bg-gradient-to-b from-slate-950 via-blue-950/20 to-slate-950">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(59,130,246,0.1),transparent_50%)]"></div>
        
        <div className="max-w-7xl mx-auto relative z-10">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-black text-center mb-4 bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 neon-text">
            Game Genres We Master
          </h2>
          <p className="text-lg md:text-xl text-center text-slate-300 mb-16 max-w-2xl mx-auto">
            Our AI excels across every mobile game category
          </p>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 md:gap-6">
            {[
              { name: "Puzzle", icon: "🧩", color: "from-purple-500 to-pink-500", delay: "0s" },
              { name: "Action", icon: "⚔️", color: "from-red-500 to-orange-500", delay: "0.1s" },
              { name: "Racing", icon: "🏎️", color: "from-yellow-500 to-red-500", delay: "0.2s" },
              { name: "RPG", icon: "🗡️", color: "from-indigo-500 to-purple-500", delay: "0.3s" },
              { name: "Strategy", icon: "♟️", color: "from-blue-500 to-cyan-500", delay: "0.4s" },
              { name: "Casual", icon: "🎮", color: "from-green-500 to-teal-500", delay: "0.5s" },
            ].map((genre, idx) => (
              <div 
                key={idx} 
                className="game-genre-card group"
                style={{animationDelay: genre.delay}}
              >
                <div className={`absolute inset-0 bg-gradient-to-br ${genre.color} rounded-2xl blur-xl opacity-30 group-hover:opacity-60 transition-all duration-500`}></div>
                <div className={`relative bg-gradient-to-br ${genre.color} bg-opacity-10 backdrop-blur-xl rounded-2xl border border-white/10 p-6 transform hover:scale-110 hover:-translate-y-2 transition-all duration-300 shadow-xl hover:shadow-2xl`}>
                  <div className="text-5xl mb-3 animate-bounce-slow" style={{animationDelay: genre.delay}}>{genre.icon}</div>
                  <h3 className="text-base md:text-lg font-bold text-white">{genre.name}</h3>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Animated Mobile Game Portfolio */}
      <div className="relative py-20 px-4 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-950/30 to-transparent"></div>
        
        <div className="max-w-7xl mx-auto relative z-10">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-black text-center mb-4 bg-clip-text text-transparent bg-gradient-to-r from-pink-400 via-purple-400 to-blue-400 neon-text">
            Tested Game Portfolio
          </h2>
          <p className="text-lg md:text-xl text-center text-slate-300 mb-16 max-w-3xl mx-auto">
            See our AI in action across diverse mobile gaming experiences
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
            {[
              { 
                title: "Candy Crusher Pro", 
                genre: "Puzzle Match-3", 
                gradient: "from-pink-500 via-purple-500 to-blue-500",
                tests: "15K+",
                bugs: "342",
                animation: "puzzle"
              },
              { 
                title: "Battle Royale Arena", 
                genre: "Action Shooter", 
                gradient: "from-red-500 via-orange-500 to-yellow-500",
                tests: "28K+",
                bugs: "891",
                animation: "action"
              },
              { 
                title: "Speed Racer Turbo", 
                genre: "Racing Arcade", 
                gradient: "from-cyan-500 via-blue-500 to-purple-500",
                tests: "12K+",
                bugs: "234",
                animation: "racing"
              },
              { 
                title: "Dragon Quest RPG", 
                genre: "Fantasy Adventure", 
                gradient: "from-purple-500 via-indigo-500 to-pink-500",
                tests: "45K+",
                bugs: "1.2K",
                animation: "rpg"
              },
              { 
                title: "Farm Builder Saga", 
                genre: "Simulation", 
                gradient: "from-green-500 via-teal-500 to-cyan-500",
                tests: "33K+",
                bugs: "567",
                animation: "farm"
              },
              { 
                title: "Tower Defense Elite", 
                genre: "Strategy TD", 
                gradient: "from-orange-500 via-red-500 to-pink-500",
                tests: "21K+",
                bugs: "445",
                animation: "tower"
              }
            ].map((game, idx) => (
              <div key={idx} className="game-card-portfolio group">
                <div className={`absolute inset-0 bg-gradient-to-br ${game.gradient} rounded-3xl blur-2xl opacity-20 group-hover:opacity-40 transition-all duration-500`}></div>
                <div className="relative bg-slate-900/80 backdrop-blur-xl rounded-3xl border border-white/10 overflow-hidden shadow-2xl hover:shadow-purple-500/30 transition-all duration-500 transform hover:scale-105 hover:-translate-y-2">
                  {/* Game Screen */}
                  <div className={`relative h-48 bg-gradient-to-br ${game.gradient} overflow-hidden game-screen-${game.animation}`}>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent"></div>
                    <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-transparent animate-shimmer"></div>
                    
                    {/* Animated Game Elements */}
                    {game.animation === 'puzzle' && (
                      <div className="absolute inset-0 grid grid-cols-4 gap-2 p-4">
                        {[...Array(12)].map((_, i) => (
                          <div key={i} className="bg-white/20 backdrop-blur rounded-lg animate-pulse-icon" style={{animationDelay: `${i * 0.1}s`}}></div>
                        ))}
                      </div>
                    )}
                    
                    {game.animation === 'action' && (
                      <>
                        <div className="absolute top-4 left-4 w-16 h-2 bg-red-500 rounded-full">
                          <div className="h-full bg-gradient-to-r from-green-500 to-red-500 rounded-full animate-health-bar"></div>
                        </div>
                        <div className="absolute top-4 right-4 text-white font-bold text-xl animate-score-count">100</div>
                        <div className="absolute bottom-1/2 left-1/2 w-8 h-8 border-4 border-white rounded-full animate-crosshair"></div>
                      </>
                    )}
                    
                    {game.animation === 'racing' && (
                      <>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <div className="w-32 h-48 border-4 border-white/30 border-dashed animate-race-track"></div>
                        </div>
                        <div className="absolute top-4 left-1/2 -translate-x-1/2">
                          <div className="text-white font-bold text-2xl animate-speed">250 KM/H</div>
                        </div>
                      </>
                    )}
                    
                    {game.animation === 'rpg' && (
                      <>
                        <div className="absolute bottom-4 left-4 right-4 bg-black/50 backdrop-blur rounded-lg p-2">
                          <div className="flex gap-2 mb-2">
                            <div className="w-12 h-12 bg-purple-500/50 rounded animate-pulse"></div>
                            <div className="flex-1">
                              <div className="h-2 bg-green-500 rounded mb-1 animate-health-bar"></div>
                              <div className="h-2 bg-blue-500 rounded animate-mana-bar"></div>
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                    
                    {game.animation === 'farm' && (
                      <div className="absolute inset-0 grid grid-cols-3 gap-2 p-4">
                        {[...Array(6)].map((_, i) => (
                          <div key={i} className="bg-green-500/20 backdrop-blur rounded-lg flex items-center justify-center">
                            <div className="text-2xl animate-grow-plant" style={{animationDelay: `${i * 0.2}s`}}>🌱</div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {game.animation === 'tower' && (
                      <>
                        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-black/80 to-transparent"></div>
                        <div className="absolute bottom-4 left-4">
                          <div className="w-8 h-12 bg-blue-500/50 rounded animate-tower-shoot"></div>
                        </div>
                        <div className="absolute top-1/3 right-1/4 w-4 h-4 bg-red-500 rounded-full animate-enemy-move"></div>
                      </>
                    )}
                  </div>
                  
                  {/* Game Info */}
                  <div className="p-6">
                    <h3 className="text-xl md:text-2xl font-bold text-white mb-2">{game.title}</h3>
                    <p className="text-sm text-slate-400 mb-4">{game.genre}</p>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-blue-500/10 rounded-lg p-3 border border-blue-400/20">
                        <div className="text-2xl font-bold text-blue-400">{game.tests}</div>
                        <div className="text-xs text-slate-400">Tests Run</div>
                      </div>
                      <div className="bg-red-500/10 rounded-lg p-3 border border-red-400/20">
                        <div className="text-2xl font-bold text-red-400">{game.bugs}</div>
                        <div className="text-xs text-slate-400">Bugs Found</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Demo Video - Investor Showcase */}
      {demoVideoUrl && (
        <div className="relative py-32 px-4 overflow-hidden">
          {/* Cinematic Background */}
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-900/20 to-transparent"></div>
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse-glow"></div>
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl animate-pulse-glow" style={{animationDelay: '1.5s'}}></div>
          
          {/* Floating Film Reels */}
          <div className="absolute top-20 left-10 w-16 h-16 border-4 border-purple-400/30 rounded-full animate-spin-slow"></div>
          <div className="absolute bottom-20 right-10 w-20 h-20 border-4 border-blue-400/30 rounded-full animate-spin-slower"></div>
          
          <div className="max-w-7xl mx-auto relative z-10">
            <div className="text-center mb-12">
              <div className="inline-block mb-4">
                <div className="px-6 py-2 bg-gradient-to-r from-purple-600/30 to-blue-600/30 rounded-full border border-purple-400/50 backdrop-blur-xl">
                  <span className="text-purple-300 text-sm font-semibold tracking-wider">🎬 INVESTOR DEMO</span>
                </div>
              </div>
              <h2 className="text-6xl md:text-7xl font-black mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 animate-gradient-x">
                See PlayMetric in Action
              </h2>
              <p className="text-2xl text-slate-300 max-w-3xl mx-auto mb-4">
                Watch our AI agents autonomously test, learn, and master mobile games
              </p>
              <div className="flex items-center justify-center gap-6 text-sm text-slate-400">
                <span className="flex items-center gap-2"><Play className="w-4 h-4 text-purple-400" /> Live Gameplay</span>
                <span className="flex items-center gap-2"><Brain className="w-4 h-4 text-blue-400" /> AI Decision Making</span>
                <span className="flex items-center gap-2"><TrendingUp className="w-4 h-4 text-pink-400" /> Real-time Analytics</span>
              </div>
            </div>
            
            <div className="relative group">
              {/* Video Container with Cinematic Effects */}
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600 to-blue-600 rounded-3xl blur-xl group-hover:blur-2xl transition-all opacity-50 animate-pulse-glow"></div>
              <div className="relative bg-gradient-to-br from-slate-900/90 to-slate-800/90 backdrop-blur-2xl rounded-3xl border-2 border-purple-500/30 p-3 shadow-2xl transform group-hover:scale-[1.02] transition-all duration-500">
                {/* Scanline Effect */}
                <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-3xl">
                  <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/5 to-transparent h-full animate-scanline"></div>
                </div>
                
                <div className="aspect-video rounded-2xl overflow-hidden bg-black shadow-inner relative">
                  {/* Video Player */}
                  <video controls className="w-full h-full" src={demoVideoUrl}>
                    Your browser does not support video playback.
                  </video>
                  
                  {/* Corner Decorations */}
                  <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-purple-400/50"></div>
                  <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-blue-400/50"></div>
                  <div className="absolute bottom-4 left-4 w-8 h-8 border-b-2 border-l-2 border-pink-400/50"></div>
                  <div className="absolute bottom-4 right-4 w-8 h-8 border-b-2 border-r-2 border-purple-400/50"></div>
                </div>
                
                {/* Video Stats */}
                <div className="mt-4 grid grid-cols-3 gap-4">
                  <div className="text-center p-3 bg-purple-900/30 rounded-xl border border-purple-500/20">
                    <div className="text-2xl font-bold text-purple-400">50K+</div>
                    <div className="text-xs text-slate-400">Test Sessions</div>
                  </div>
                  <div className="text-center p-3 bg-blue-900/30 rounded-xl border border-blue-500/20">
                    <div className="text-2xl font-bold text-blue-400">98.7%</div>
                    <div className="text-xs text-slate-400">Accuracy</div>
                  </div>
                  <div className="text-center p-3 bg-pink-900/30 rounded-xl border border-pink-500/20">
                    <div className="text-2xl font-bold text-pink-400">24/7</div>
                    <div className="text-xs text-slate-400">Automation</div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Trust Badges */}
            <div className="mt-12 flex flex-wrap items-center justify-center gap-6">
              <div className="px-6 py-3 bg-gradient-to-r from-green-900/30 to-green-800/30 rounded-full border border-green-500/30 backdrop-blur-xl flex items-center gap-3">
                <Shield className="w-5 h-5 text-green-400" />
                <span className="text-green-300 font-semibold">Enterprise Ready</span>
              </div>
              <div className="px-6 py-3 bg-gradient-to-r from-blue-900/30 to-blue-800/30 rounded-full border border-blue-500/30 backdrop-blur-xl flex items-center gap-3">
                <Zap className="w-5 h-5 text-blue-400" />
                <span className="text-blue-300 font-semibold">Real-time Processing</span>
              </div>
              <div className="px-6 py-3 bg-gradient-to-r from-purple-900/30 to-purple-800/30 rounded-full border border-purple-500/30 backdrop-blur-xl flex items-center gap-3">
                <Globe className="w-5 h-5 text-purple-400" />
                <span className="text-purple-300 font-semibold">Cloud Scalable</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* How It Works - 3 Step Process */}
      <div className="relative py-20 px-4">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-5xl md:text-6xl font-black text-center mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
            How It Works
          </h2>
          <p className="text-xl text-center text-slate-300 mb-16 max-w-2xl mx-auto">
            From upload to insights - automated game testing in three powerful steps
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-blue-800 rounded-3xl blur-xl group-hover:blur-2xl transition-all opacity-50"></div>
              <div className="relative bg-gradient-to-br from-blue-900/80 to-blue-950/80 backdrop-blur-xl rounded-3xl border border-blue-500/30 p-8 transform group-hover:scale-105 transition-all duration-500 h-full">
                <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center mb-6 shadow-xl">
                  <div className="text-4xl font-black text-white">1</div>
                </div>
                <Upload className="w-12 h-12 text-blue-400 mb-4" />
                <h3 className="text-2xl font-bold text-white mb-4">Upload Game</h3>
                <ul className="space-y-3 text-blue-200">
                  <li className="flex items-start gap-3">
                    <Smartphone className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                    <span>Upload Android APK files</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Play className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                    <span>Add optional training videos</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Database className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                    <span>Automatic metadata extraction</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Step 2 */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600 to-purple-800 rounded-3xl blur-xl group-hover:blur-2xl transition-all opacity-50"></div>
              <div className="relative bg-gradient-to-br from-purple-900/80 to-purple-950/80 backdrop-blur-xl rounded-3xl border border-purple-500/30 p-8 transform group-hover:scale-105 transition-all duration-500 h-full">
                <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-purple-700 rounded-2xl flex items-center justify-center mb-6 shadow-xl">
                  <div className="text-4xl font-black text-white">2</div>
                </div>
                <Brain className="w-12 h-12 text-purple-400 mb-4" />
                <h3 className="text-2xl font-bold text-white mb-4">AI Learning</h3>
                <ul className="space-y-3 text-purple-200">
                  <li className="flex items-start gap-3">
                    <Eye className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>Frame-by-frame analysis</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Brain className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>BLIP-2 & Gemini Vision AI</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Database className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <span>Knowledge base construction</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Step 3 */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-green-600 to-teal-600 rounded-3xl blur-xl group-hover:blur-2xl transition-all opacity-50"></div>
              <div className="relative bg-gradient-to-br from-green-900/80 to-teal-950/80 backdrop-blur-xl rounded-3xl border border-green-500/30 p-8 transform group-hover:scale-105 transition-all duration-500 h-full">
                <div className="w-20 h-20 bg-gradient-to-br from-green-500 to-teal-700 rounded-2xl flex items-center justify-center mb-6 shadow-xl">
                  <div className="text-4xl font-black text-white">3</div>
                </div>
                <Rocket className="w-12 h-12 text-green-400 mb-4" />
                <h3 className="text-2xl font-bold text-white mb-4">AI Testing</h3>
                <ul className="space-y-3 text-green-200">
                  <li className="flex items-start gap-3">
                    <Play className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <span>Autonomous gameplay</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <Shield className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <span>Real-time bug detection</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <TrendingUp className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <span>Comprehensive reporting</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Technology Tree */}
      <div className="relative py-16 md:py-24 px-4 overflow-hidden bg-gradient-to-b from-slate-900/30 via-purple-950/10 to-slate-900/30">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(139,92,246,0.05),transparent_70%)]"></div>
        
        <div className="max-w-7xl mx-auto relative">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-black text-center mb-4 bg-clip-text text-transparent bg-gradient-to-r from-green-400 via-teal-400 to-blue-400">
            Technology Tree
          </h2>
          <p className="text-lg md:text-xl text-center text-slate-300 mb-12 md:mb-16 max-w-2xl mx-auto">
            Growing innovation from roots to cloud
          </p>

          <div className="relative max-w-5xl mx-auto">
            {/* Tree Trunk SVG */}
            <div className="absolute left-1/2 -translate-x-1/2 top-0 bottom-0 w-1 opacity-20">
              <div className="w-full h-full bg-gradient-to-b from-transparent via-orange-500 to-transparent tree-trunk"></div>
            </div>

            {/* Roots - Database Layer */}
            <div className="relative mb-10 md:mb-12">
              <div className="text-center mb-5 md:mb-6">
                <div className="inline-block px-4 md:px-5 py-2 md:py-2.5 bg-orange-900/30 backdrop-blur-lg rounded-full border border-orange-400/20 shadow-lg shadow-orange-500/10">
                  <span className="text-orange-200 font-semibold text-sm md:text-base">🌱 Roots - Data Foundation</span>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-5">
                {[
                  { icon: Database, title: "PostgreSQL", desc: "TimescaleDB", color: "from-orange-500 to-orange-700", glow: "orange" },
                  { icon: Zap, title: "Redis", desc: "Real-time cache", color: "from-red-500 to-red-700", glow: "red" },
                  { icon: Globe, title: "Docker", desc: "Containers", color: "from-pink-500 to-pink-700", glow: "pink" }
                ].map((tech, idx) => (
                  <div key={idx} className="tech-card group">
                    <div className={`absolute inset-0 bg-gradient-to-br ${tech.color} rounded-2xl blur-lg opacity-30 group-hover:opacity-50 transition-all duration-300`}></div>
                    <div className={`relative bg-gradient-to-br ${tech.color} bg-opacity-20 backdrop-blur-xl rounded-2xl border border-white/10 p-5 md:p-6 transform hover:scale-105 transition-all duration-300 shadow-lg`}>
                      <tech.icon className="w-8 h-8 md:w-10 md:h-10 text-white mb-2 md:mb-3 drop-shadow-lg" />
                      <h4 className="font-bold text-white mb-1.5 md:mb-2 text-base md:text-lg">{tech.title}</h4>
                      <p className="text-xs md:text-sm text-white/80">{tech.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Branch Line */}
            <div className="flex justify-center mb-8">
              <div className="h-16 w-1 bg-gradient-to-b from-orange-500/50 to-blue-500/50 rounded-full tree-branch"></div>
            </div>

            {/* Trunk - Core Services */}
            <div className="relative mb-10 md:mb-12">
              <div className="text-center mb-5 md:mb-6">
                <div className="inline-block px-4 md:px-5 py-2 md:py-2.5 bg-blue-900/30 backdrop-blur-lg rounded-full border border-blue-400/20 shadow-lg shadow-blue-500/10">
                  <span className="text-blue-200 font-semibold text-sm md:text-base">🌳 Trunk - Core Engine</span>
                </div>
              </div>
              
              <div className="tech-card group">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/30 to-purple-500/30 rounded-3xl blur-2xl opacity-30 group-hover:opacity-50 transition-all duration-500"></div>
                <div className="relative bg-gradient-to-br from-slate-800/60 to-slate-900/60 backdrop-blur-xl rounded-3xl border border-blue-400/20 p-6 md:p-8 shadow-2xl">
                  <div className="text-center mb-5 md:mb-6">
                    <Code2 className="w-12 h-12 md:w-16 md:h-16 text-blue-300 mx-auto mb-3 md:mb-4 drop-shadow-lg" />
                    <h3 className="text-2xl md:text-3xl font-bold text-white mb-2">FastAPI Orchestrator</h3>
                    <p className="text-slate-200 text-sm md:text-base">Coordinating all microservices</p>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                    {[
                      { icon: Eye, label: "Vision", color: "blue" },
                      { icon: Brain, label: "Learning", color: "purple" },
                      { icon: Play, label: "AI Player", color: "green" },
                      { icon: TrendingUp, label: "Analytics", color: "orange" }
                    ].map((service, idx) => (
                      <div key={idx} className={`text-center p-3 md:p-4 bg-${service.color}-900/10 rounded-xl border border-${service.color}-400/10 hover:bg-${service.color}-900/30 hover:border-${service.color}-400/30 transition-all duration-300 cursor-pointer hover:scale-105 shadow-lg`}>
                        <service.icon className={`w-6 h-6 md:w-8 md:h-8 text-${service.color}-300 mx-auto mb-1.5 md:mb-2`} />
                        <div className="text-xs md:text-sm text-slate-200 font-medium">{service.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Branch Lines */}
            <div className="flex justify-center gap-8 mb-8">
              <div className="h-12 w-1 bg-gradient-to-b from-purple-500/50 to-green-500/50 rounded-full tree-branch" style={{animationDelay: '0.2s'}}></div>
              <div className="h-16 w-1 bg-gradient-to-b from-purple-500/50 to-pink-500/50 rounded-full tree-branch" style={{animationDelay: '0.4s'}}></div>
              <div className="h-12 w-1 bg-gradient-to-b from-purple-500/50 to-blue-500/50 rounded-full tree-branch" style={{animationDelay: '0.6s'}}></div>
              <div className="h-14 w-1 bg-gradient-to-b from-purple-500/50 to-cyan-500/50 rounded-full tree-branch" style={{animationDelay: '0.8s'}}></div>
            </div>

            {/* Branches - AI Models */}
            <div className="relative mb-10 md:mb-12">
              <div className="text-center mb-5 md:mb-6">
                <div className="inline-block px-4 md:px-5 py-2 md:py-2.5 bg-purple-900/30 backdrop-blur-lg rounded-full border border-purple-400/20 shadow-lg shadow-purple-500/10">
                  <span className="text-purple-200 font-semibold text-sm md:text-base">🧠 Branches - AI Intelligence</span>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
                {[
                  { icon: Brain, title: "BLIP-2", desc: "Image captioning", gradient: "from-blue-500 to-blue-700" },
                  { icon: Eye, title: "Gemini Vision", desc: "Visual AI", gradient: "from-purple-500 to-purple-700" },
                  { icon: Code2, title: "Tesseract OCR", desc: "Text detection", gradient: "from-green-500 to-green-700" },
                  { icon: Zap, title: "Deep Q-Network", desc: "RL engine", gradient: "from-pink-500 to-pink-700" }
                ].map((tech, idx) => (
                  <div key={idx} className="tech-card group">
                    <div className={`absolute inset-0 bg-gradient-to-br ${tech.gradient} rounded-2xl blur-lg opacity-30 group-hover:opacity-50 transition-all duration-300`}></div>
                    <div className={`relative bg-gradient-to-br ${tech.gradient} bg-opacity-20 backdrop-blur-xl rounded-2xl border border-white/10 p-5 md:p-6 transform hover:scale-105 hover:rotate-1 transition-all duration-300 shadow-lg`}>
                      <tech.icon className="w-8 h-8 md:w-10 md:h-10 text-white mb-2 md:mb-3 drop-shadow-lg" />
                      <h4 className="font-bold text-white mb-1.5 md:mb-2 text-sm md:text-base">{tech.title}</h4>
                      <p className="text-xs text-white/80">{tech.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Branch Line */}
            <div className="flex justify-center mb-8">
              <div className="h-12 w-1 bg-gradient-to-b from-pink-500/50 to-cyan-500/50 rounded-full tree-branch"></div>
            </div>

            {/* Leaves - Frontend */}
            <div className="relative">
              <div className="text-center mb-5 md:mb-6">
                <div className="inline-block px-4 md:px-5 py-2 md:py-2.5 bg-cyan-900/30 backdrop-blur-lg rounded-full border border-cyan-400/20 shadow-lg shadow-cyan-500/10">
                  <span className="text-cyan-200 font-semibold text-sm md:text-base">🍃 Canopy - User Interface</span>
                </div>
              </div>
              
              <div className="tech-card group max-w-md mx-auto">
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/30 to-cyan-700/30 rounded-2xl blur-xl opacity-30 group-hover:opacity-50 transition-all duration-300"></div>
                <div className="relative bg-gradient-to-br from-cyan-900/40 to-cyan-950/40 backdrop-blur-xl rounded-2xl border border-cyan-400/20 p-5 md:p-6 transform hover:scale-105 transition-all duration-300 shadow-lg">
                  <Globe className="w-10 h-10 md:w-12 md:h-12 text-cyan-300 mb-2 md:mb-3 mx-auto drop-shadow-lg" />
                  <h4 className="font-bold text-white mb-1.5 md:mb-2 text-center text-lg md:text-xl">React Dashboard</h4>
                  <p className="text-xs md:text-sm text-cyan-100 text-center">TypeScript + Vite + TailwindCSS + WebSockets</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Features */}
      <div className="relative py-16 md:py-24 px-4 bg-gradient-to-b from-transparent via-slate-900/20 to-transparent">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-black text-center mb-12 md:mb-16 bg-clip-text text-transparent bg-gradient-to-r from-orange-400 via-red-400 to-pink-400">
            Platform Features
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
            {[
              { icon: Shield, title: "Bug Detection", desc: "Catches crashes, ANRs, freezes automatically", gradient: "from-green-500 to-green-700" },
              { icon: Brain, title: "Learn from Videos", desc: "AI learns from gameplay demonstrations", gradient: "from-purple-500 to-purple-700" },
              { icon: TrendingUp, title: "Difficulty Analysis", desc: "Track completion rates and balancing", gradient: "from-blue-500 to-blue-700" },
              { icon: Database, title: "Version Compare", desc: "Identify regressions across versions", gradient: "from-orange-500 to-orange-700" },
              { icon: Zap, title: "Real-time Updates", desc: "Live WebSocket monitoring", gradient: "from-yellow-500 to-yellow-700" },
              { icon: Rocket, title: "24/7 Autonomous", desc: "Continuous testing without humans", gradient: "from-pink-500 to-pink-700" },
            ].map((feature, idx) => (
              <div key={idx} className="group relative">
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} rounded-2xl blur-xl opacity-20 group-hover:opacity-40 transition-all duration-300`}></div>
                <div className={`relative bg-gradient-to-br ${feature.gradient} bg-opacity-15 backdrop-blur-xl rounded-2xl border border-white/10 p-5 md:p-6 transform hover:scale-105 hover:-translate-y-1 transition-all duration-300 shadow-lg hover:shadow-xl h-full`}>
                  <feature.icon className="w-10 h-10 md:w-12 md:h-12 text-white mb-3 md:mb-4 drop-shadow-lg" />
                  <h3 className="text-lg md:text-xl font-bold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-200 text-sm leading-relaxed">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="relative py-16 md:py-20 px-4 overflow-hidden bg-gradient-to-b from-transparent via-blue-950/20 to-transparent">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.05),transparent_70%)]"></div>
        <div className="relative max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-black mb-4 md:mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
            Ready to Transform Your QA?
          </h2>
          <p className="text-lg md:text-xl text-slate-200 mb-8 md:mb-10 px-4 max-w-2xl mx-auto">
            Join the future of mobile game testing with AI-powered automation
          </p>
          <a href="/login" className="inline-block px-6 md:px-8 py-3 md:py-4 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 rounded-full font-bold text-white text-base md:text-lg shadow-xl shadow-purple-500/30 hover:shadow-purple-500/60 transform hover:scale-105 transition-all duration-300">
            Get Started Now →
          </a>
        </div>
      </div>

      {/* Footer */}
      <div className="relative py-8 md:py-10 px-4 border-t border-slate-800/50 bg-slate-950/50">
        <div className="max-w-7xl mx-auto text-center">
          <img src="/logo.png" alt="PlayMetric" className="h-10 md:h-12 mx-auto mb-3 md:mb-4 opacity-40 hover:opacity-60 transition-opacity" />
          <p className="text-slate-300 text-base md:text-lg mb-2">
            PlayMetric - AI-Powered Mobile Game Testing Platform
          </p>
          <p className="text-slate-400 text-xs md:text-sm">
            © 2025 PlayMetric. Built with ❤️ for the future of automated testing.
          </p>
        </div>
      </div>

      {/* Custom Animations */}
      <style>{`
        /* ===== GRID BACKGROUND ===== */
        .bg-grid-pattern {
          background-image: 
            linear-gradient(rgba(59,130,246,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(147,51,234,0.1) 1px, transparent 1px);
          background-size: 50px 50px;
        }
        @keyframes grid-flow {
          0% { background-position: 0 0; }
          100% { background-position: 50px 50px; }
        }
        .animate-grid-flow {
          animation: grid-flow 20s linear infinite;
        }

        /* ===== HOLOGRAPHIC & NEON EFFECTS ===== */
        .holographic-effect {
          position: relative;
        }
        .holographic-effect::before {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(
            45deg,
            transparent 30%,
            rgba(255,255,255,0.1) 50%,
            transparent 70%
          );
          background-size: 200% 200%;
          animation: holographic-shift 3s ease-in-out infinite;
        }
        @keyframes holographic-shift {
          0%, 100% { background-position: 0% 0%; }
          50% { background-position: 100% 100%; }
        }

        @keyframes shimmer {
          0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
          100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
        }
        .animate-shimmer {
          animation: shimmer 3s ease-in-out infinite;
        }

        .neon-text {
          text-shadow: 
            0 0 10px rgba(147,51,234,0.8),
            0 0 20px rgba(147,51,234,0.6),
            0 0 30px rgba(147,51,234,0.4),
            0 0 40px rgba(147,51,234,0.2);
        }

        .neon-ring {
          box-shadow: 
            0 0 10px currentColor,
            inset 0 0 10px currentColor;
        }
        .neon-ring-small {
          box-shadow: 
            0 0 5px currentColor,
            inset 0 0 5px currentColor;
        }

        .neon-border {
          box-shadow: 
            0 0 5px rgba(59,130,246,0.5),
            0 0 10px rgba(59,130,246,0.3);
        }

        /* ===== PHONE EFFECTS ===== */
        .phone-3d {
          perspective: 1000px;
          transform-style: preserve-3d;
        }

        .phone-glow-blue {
          box-shadow: 
            0 20px 60px rgba(59,130,246,0.4),
            0 0 30px rgba(59,130,246,0.2);
        }
        .phone-glow-green {
          box-shadow: 
            0 20px 60px rgba(34,197,94,0.4),
            0 0 30px rgba(34,197,94,0.2);
        }
        .phone-glow-orange {
          box-shadow: 
            0 20px 60px rgba(249,115,22,0.4),
            0 0 30px rgba(249,115,22,0.2);
        }
        .phone-glow-purple {
          box-shadow: 
            0 20px 60px rgba(168,85,247,0.4),
            0 0 30px rgba(168,85,247,0.2);
        }

        @keyframes pulse-icon {
          0%, 100% { opacity: 0.6; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.05); }
        }
        .animate-pulse-icon {
          animation: pulse-icon 2s ease-in-out infinite;
        }

        /* ===== GLITCH EFFECTS ===== */
        .glitch-text {
          position: relative;
        }
        .glitch-text::before,
        .glitch-text::after {
          content: attr(data-text);
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
        }
        .glitch-text::before {
          animation: glitch-1 2.5s infinite;
          color: rgba(59,130,246,0.8);
          z-index: -1;
        }
        .glitch-text::after {
          animation: glitch-2 2.5s infinite;
          color: rgba(236,72,153,0.8);
          z-index: -2;
        }
        @keyframes glitch-1 {
          0%, 100% { transform: translate(0); }
          20% { transform: translate(-2px, 2px); }
          40% { transform: translate(-2px, -2px); }
          60% { transform: translate(2px, 2px); }
          80% { transform: translate(2px, -2px); }
        }
        @keyframes glitch-2 {
          0%, 100% { transform: translate(0); }
          20% { transform: translate(2px, -2px); }
          40% { transform: translate(2px, 2px); }
          60% { transform: translate(-2px, -2px); }
          80% { transform: translate(-2px, 2px); }
        }

        @keyframes glitch {
          0%, 100% { transform: translate(0); }
          33% { transform: translate(-5px, 0); }
          66% { transform: translate(5px, 0); }
        }
        .animate-glitch {
          animation: glitch 5s ease-in-out infinite;
        }

        /* ===== MATRIX RAIN ===== */
        @keyframes matrix-rain {
          0% { transform: translateY(-100%); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { transform: translateY(100vh); opacity: 0; }
        }
        .animate-matrix-rain {
          animation: matrix-rain linear infinite;
        }

        /* ===== SCANLINE ===== */
        @keyframes scanline {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100vh); }
        }
        .animate-scanline {
          animation: scanline 6s linear infinite;
        }

        /* ===== GLOW EFFECTS ===== */
        .logo-glow {
          filter: drop-shadow(0 0 30px rgba(147,51,234,0.6));
        }

        .glow-blue {
          box-shadow: 0 0 10px rgba(59,130,246,0.6);
        }
        .glow-purple {
          box-shadow: 0 0 10px rgba(147,51,234,0.6);
        }
        .glow-pink {
          box-shadow: 0 0 10px rgba(236,72,153,0.6);
        }
        .glow-green {
          box-shadow: 0 0 10px rgba(34,197,94,0.6);
        }

        .badge-glow-blue {
          box-shadow: 
            0 0 15px rgba(59,130,246,0.3),
            inset 0 0 15px rgba(59,130,246,0.1);
        }
        .badge-glow-blue:hover {
          box-shadow: 
            0 0 25px rgba(59,130,246,0.6),
            inset 0 0 20px rgba(59,130,246,0.2);
        }
        .badge-glow-purple {
          box-shadow: 
            0 0 15px rgba(147,51,234,0.3),
            inset 0 0 15px rgba(147,51,234,0.1);
        }
        .badge-glow-purple:hover {
          box-shadow: 
            0 0 25px rgba(147,51,234,0.6),
            inset 0 0 20px rgba(147,51,234,0.2);
        }
        .badge-glow-pink {
          box-shadow: 
            0 0 15px rgba(236,72,153,0.3),
            inset 0 0 15px rgba(236,72,153,0.1);
        }
        .badge-glow-pink:hover {
          box-shadow: 
            0 0 25px rgba(236,72,153,0.6),
            inset 0 0 20px rgba(236,72,153,0.2);
        }

        @keyframes pulse-glow {
          0%, 100% { opacity: 0.6; filter: blur(40px); }
          50% { opacity: 1; filter: blur(60px); }
        }
        .animate-pulse-glow {
          animation: pulse-glow 4s ease-in-out infinite;
        }

        /* ===== ROTATION ANIMATIONS ===== */
        @keyframes spin-very-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-very-slow {
          animation: spin-very-slow 20s linear infinite;
        }

        @keyframes spin-slow-reverse {
          from { transform: rotate(0deg); }
          to { transform: rotate(-360deg); }
        }
        .animate-spin-slow-reverse {
          animation: spin-slow-reverse 15s linear infinite;
        }

        .animate-float-reverse {
          animation: float-reverse 4s ease-in-out infinite;
        }
        @keyframes float-reverse {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(20px); }
        }

        /* ===== FADE IN ANIMATION ===== */
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fade-in-up {
          animation: fade-in-up 1s ease-out;
        }

        /* ===== EXISTING ANIMATIONS ===== */
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }
        @keyframes gradient {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        @keyframes float-slow {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          33% { transform: translateY(-15px) translateX(5px); }
          66% { transform: translateY(-5px) translateX(-5px); }
        }
        @keyframes float-slower {
          0%, 100% { transform: translateY(0px) translateX(0px) scale(1); }
          50% { transform: translateY(-25px) translateX(10px) scale(1.2); }
        }
        @keyframes phone-float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          33% { transform: translateY(-20px) rotate(2deg); }
          66% { transform: translateY(-10px) rotate(-2deg); }
        }
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        @keyframes tree-grow {
          0% { transform: scaleY(0); opacity: 0; }
          100% { transform: scaleY(1); opacity: 1; }
        }
        @keyframes leaf-appear {
          0% { transform: scale(0) rotate(-180deg); opacity: 0; }
          100% { transform: scale(1) rotate(0deg); opacity: 1; }
        }
        .animate-float {
          animation: float 3s ease-in-out infinite;
        }
        .animate-gradient {
          background-size: 200% 200%;
          animation: gradient 3s ease infinite;
        }
        .animate-float-slow {
          animation: float-slow 6s ease-in-out infinite;
        }
        .animate-float-slower {
          animation: float-slower 8s ease-in-out infinite;
        }
        .phone-float {
          animation: phone-float 5s ease-in-out infinite;
        }
        .animate-spin-slow {
          animation: spin-slow 3s linear infinite;
        }
        .animate-pulse-slow {
          animation: pulse-slow 3s ease-in-out infinite;
        }
        .tree-trunk {
          animation: tree-grow 1s ease-out forwards;
          transform-origin: top;
        }
        .tree-branch {
          animation: tree-grow 0.8s ease-out forwards;
          transform-origin: top;
        }
        .tech-card {
          animation: leaf-appear 0.6s ease-out forwards;
          position: relative;
        }
        
        /* Glowing effects */
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.5); }
          50% { box-shadow: 0 0 40px rgba(147, 51, 234, 0.8); }
        }
        .tech-card:hover {
          animation: glow 2s ease-in-out infinite;
        }

        /* ===== GAME-SPECIFIC ANIMATIONS ===== */
        
        /* Game Genre Cards */
        @keyframes genre-card-appear {
          0% { 
            opacity: 0; 
            transform: scale(0.5) rotate(-180deg); 
          }
          100% { 
            opacity: 1; 
            transform: scale(1) rotate(0deg); 
          }
        }
        .game-genre-card {
          animation: genre-card-appear 0.6s ease-out forwards;
          position: relative;
        }

        @keyframes bounce-slow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        .animate-bounce-slow {
          animation: bounce-slow 2s ease-in-out infinite;
        }

        /* Portfolio Cards */
        @keyframes portfolio-card-slide-up {
          0% {
            opacity: 0;
            transform: translateY(50px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .game-card-portfolio {
          animation: portfolio-card-slide-up 0.8s ease-out forwards;
          position: relative;
        }

        /* Puzzle Game Animation */
        .game-screen-puzzle {
          animation: screen-glow 3s ease-in-out infinite;
        }

        /* Action Game Animations */
        @keyframes health-bar {
          0%, 100% { width: 100%; }
          50% { width: 30%; }
        }
        .animate-health-bar {
          animation: health-bar 4s ease-in-out infinite;
        }

        @keyframes score-count {
          0% { transform: scale(1); }
          50% { transform: scale(1.2); color: #fbbf24; }
          100% { transform: scale(1); }
        }
        .animate-score-count {
          animation: score-count 2s ease-in-out infinite;
        }

        @keyframes crosshair {
          0%, 100% { 
            transform: translate(-50%, -50%) scale(1); 
            opacity: 1; 
          }
          50% { 
            transform: translate(-50%, -50%) scale(1.5); 
            opacity: 0.5; 
          }
        }
        .animate-crosshair {
          animation: crosshair 1s ease-in-out infinite;
        }

        /* Racing Game Animations */
        @keyframes race-track {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
        .animate-race-track {
          animation: race-track 2s linear infinite;
        }

        @keyframes speed {
          0%, 100% { transform: scale(1); color: white; }
          50% { transform: scale(1.1); color: #3b82f6; }
        }
        .animate-speed {
          animation: speed 1.5s ease-in-out infinite;
        }

        /* RPG Game Animations */
        @keyframes mana-bar {
          0%, 100% { width: 100%; background-color: #3b82f6; }
          50% { width: 50%; background-color: #8b5cf6; }
        }
        .animate-mana-bar {
          animation: mana-bar 3s ease-in-out infinite;
        }

        /* Farm Game Animations */
        @keyframes grow-plant {
          0% { 
            transform: scale(0.5); 
            filter: grayscale(100%);
          }
          100% { 
            transform: scale(1); 
            filter: grayscale(0%);
          }
        }
        .animate-grow-plant {
          animation: grow-plant 2s ease-out infinite;
        }

        /* Tower Defense Animations */
        @keyframes tower-shoot {
          0%, 90%, 100% { 
            box-shadow: 0 0 0 transparent; 
          }
          95% { 
            box-shadow: 0 0 20px rgba(59,130,246,0.8); 
          }
        }
        .animate-tower-shoot {
          animation: tower-shoot 3s ease-in-out infinite;
        }

        @keyframes enemy-move {
          0% { 
            transform: translate(0, 0); 
          }
          100% { 
            transform: translate(-200px, 100px); 
            opacity: 0;
          }
        }
        .animate-enemy-move {
          animation: enemy-move 4s linear infinite;
        }

        /* Mobile Phone Swipe Animation */
        @keyframes swipe-gesture {
          0%, 100% { transform: translateX(-20px); opacity: 0; }
          50% { transform: translateX(20px); opacity: 1; }
        }
        .animate-swipe-gesture {
          animation: swipe-gesture 2s ease-in-out infinite;
        }

        /* Tap Indicator */
        @keyframes tap-ripple {
          0% { 
            transform: scale(0); 
            opacity: 1; 
          }
          100% { 
            transform: scale(2); 
            opacity: 0; 
          }
        }
        .animate-tap-ripple {
          animation: tap-ripple 1.5s ease-out infinite;
        }

        /* Gaming Stats Counter */
        @keyframes count-up {
          0% { transform: translateY(20px); opacity: 0; }
          100% { transform: translateY(0); opacity: 1; }
        }
        .animate-count-up {
          animation: count-up 0.5s ease-out forwards;
        }

        /* Achievement Badge Pop */
        @keyframes badge-pop {
          0% { 
            transform: scale(0) rotate(-180deg); 
            opacity: 0; 
          }
          50% { 
            transform: scale(1.2) rotate(10deg); 
          }
          100% { 
            transform: scale(1) rotate(0deg); 
            opacity: 1; 
          }
        }
        .animate-badge-pop {
          animation: badge-pop 0.6s cubic-bezier(0.68, -0.55, 0.265, 1.55) forwards;
        }

        /* Screen Glow Effect */
        @keyframes screen-glow {
          0%, 100% { 
            box-shadow: inset 0 0 30px rgba(147,51,234,0.3); 
          }
          50% { 
            box-shadow: inset 0 0 50px rgba(59,130,246,0.5); 
          }
        }

        /* Joystick Movement */
        @keyframes joystick-move {
          0%, 100% { transform: translate(0, 0); }
          25% { transform: translate(5px, -5px); }
          50% { transform: translate(-5px, 5px); }
          75% { transform: translate(5px, 5px); }
        }
        .animate-joystick {
          animation: joystick-move 4s ease-in-out infinite;
        }

        /* Loading Bar */
        @keyframes loading-bar {
          0% { width: 0%; }
          100% { width: 100%; }
        }
        .animate-loading-bar {
          animation: loading-bar 3s ease-in-out infinite;
        }

        /* Combo Counter */
        @keyframes combo-flash {
          0%, 100% { 
            transform: scale(1); 
            color: white; 
            text-shadow: 0 0 10px rgba(255,255,255,0.5); 
          }
          50% { 
            transform: scale(1.5); 
            color: #fbbf24; 
            text-shadow: 0 0 30px rgba(251,191,36,0.8); 
          }
        }
        .animate-combo {
          animation: combo-flash 0.5s ease-in-out;
        }

        /* Level Up Effect */
        @keyframes level-up {
          0% { 
            transform: scale(0.8) translateY(20px); 
            opacity: 0; 
          }
          50% { 
            transform: scale(1.2) translateY(-10px); 
          }
          100% { 
            transform: scale(1) translateY(0); 
            opacity: 1; 
          }
        }
        .animate-level-up {
          animation: level-up 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }

        /* Coin Collect */
        @keyframes coin-collect {
          0% { 
            transform: translateY(0) scale(1); 
            opacity: 1; 
          }
          100% { 
            transform: translateY(-100px) scale(0.5); 
            opacity: 0; 
          }
        }
        .animate-coin-collect {
          animation: coin-collect 1s ease-in forwards;
        }

        /* Power-Up Pulse */
        @keyframes power-up-pulse {
          0%, 100% { 
            transform: scale(1); 
            filter: brightness(1); 
          }
          50% { 
            transform: scale(1.1); 
            filter: brightness(1.5) saturate(1.5); 
          }
        }
        .animate-power-up {
          animation: power-up-pulse 1s ease-in-out infinite;
        }
      
        /* Spin Slow */
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 20s linear infinite;
        }
        .animate-spin-slower {
          animation: spin-slow 30s linear infinite reverse;
        }
        
        /* Gradient Animation */
        @keyframes gradient-x {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .animate-gradient-x {
          background-size: 200% auto;
          animation: gradient-x 3s ease infinite;
        }
        
        /* Particle Float */
        @keyframes particle-float {
          0%, 100% { 
            transform: translate(0, 0) rotate(0deg);
            opacity: 0.3;
          }
          25% { 
            transform: translate(100px, -50px) rotate(90deg);
            opacity: 0.7;
          }
          50% { 
            transform: translate(200px, -100px) rotate(180deg);
            opacity: 0.3;
          }
          75% { 
            transform: translate(100px, -150px) rotate(270deg);
            opacity: 0.7;
          }
        }
        .animate-particle-float {
          animation: particle-float 15s ease-in-out infinite;
        }
        
        /* Neon Border */
        @keyframes neon-border {
          0%, 100% { 
            border-color: rgba(139, 92, 246, 0.5);
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
          }
          50% { 
            border-color: rgba(59, 130, 246, 0.8);
            box-shadow: 0 0 40px rgba(59, 130, 246, 0.6);
          }
        }
        .animate-neon-border {
          animation: neon-border 2s ease-in-out infinite;
        }
        
        /* Mobile Game Icons */
        @keyframes icon-bounce {
          0%, 100% { transform: translateY(0) scale(1); }
          50% { transform: translateY(-10px) scale(1.1); }
        }
        .animate-icon-bounce {
          animation: icon-bounce 2s ease-in-out infinite;
        }
        
        /* Star Twinkle */
        @keyframes star-twinkle {
          0%, 100% { 
            opacity: 0.3;
            transform: scale(0.8);
          }
          50% { 
            opacity: 1;
            transform: scale(1.2);
          }
        }
        .animate-star-twinkle {
          animation: star-twinkle 3s ease-in-out infinite;
        }
      `}</style>
      
      {/* Contact Section for Investors */}
      <div className="relative py-32 px-4 overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-purple-950/50 to-blue-950"></div>
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-purple-500 to-transparent"></div>
          <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-blue-500 to-transparent"></div>
        </div>
        
        {/* Floating Particles */}
        {[...Array(15)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-purple-400 rounded-full animate-particle-float"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${10 + Math.random() * 10}s`
            }}
          />
        ))}
        
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="text-center mb-16">
            <div className="inline-block mb-6">
              <div className="px-6 py-2 bg-gradient-to-r from-blue-600/30 to-purple-600/30 rounded-full border border-blue-400/50 backdrop-blur-xl">
                <span className="text-blue-300 text-sm font-semibold tracking-wider">💼 GET IN TOUCH</span>
              </div>
            </div>
            <h2 className="text-6xl md:text-7xl font-black mb-6 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
              Let's Build the Future
            </h2>
            <p className="text-2xl text-slate-300 max-w-3xl mx-auto">
              Partner with us to revolutionize mobile game testing with AI
            </p>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            {/* Contact Info Cards */}
            <div className="space-y-6">
              {/* Email */}
              <div className="group relative">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl blur-xl group-hover:blur-2xl transition-all opacity-30"></div>
                <div className="relative bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-xl rounded-2xl border border-blue-500/30 p-6 transform group-hover:scale-105 transition-all duration-300">
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                      <Mail className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white mb-2">Email Us</h3>
                      <a href="mailto:investors@playmetric.ai" className="text-blue-400 hover:text-blue-300 transition-colors text-lg">
                        investors@playmetric.ai
                      </a>
                      <p className="text-slate-400 text-sm mt-2">For investment inquiries and partnerships</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Phone */}
              <div className="group relative">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-600 to-pink-600 rounded-2xl blur-xl group-hover:blur-2xl transition-all opacity-30"></div>
                <div className="relative bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-xl rounded-2xl border border-purple-500/30 p-6 transform group-hover:scale-105 transition-all duration-300">
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-700 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                      <Phone className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white mb-2">Call Us</h3>
                      <a href="tel:+1-555-PLAYMET" className="text-purple-400 hover:text-purple-300 transition-colors text-lg">
                        +1 (555) PLAY-MET
                      </a>
                      <p className="text-slate-400 text-sm mt-2">Mon-Fri, 9AM-6PM PST</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Location */}
              <div className="group relative">
                <div className="absolute inset-0 bg-gradient-to-br from-pink-600 to-orange-600 rounded-2xl blur-xl group-hover:blur-2xl transition-all opacity-30"></div>
                <div className="relative bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-xl rounded-2xl border border-pink-500/30 p-6 transform group-hover:scale-105 transition-all duration-300">
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 bg-gradient-to-br from-pink-500 to-pink-700 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                      <MapPin className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-white mb-2">Visit Us</h3>
                      <p className="text-pink-400 text-lg">
                        San Francisco, CA
                      </p>
                      <p className="text-slate-400 text-sm mt-2">Global HQ - Innovation District</p>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Quick Stats */}
              <div className="grid grid-cols-2 gap-4 mt-8">
                <div className="relative group">
                  <div className="absolute inset-0 bg-green-600 rounded-xl blur-lg opacity-30 group-hover:opacity-50 transition-opacity"></div>
                  <div className="relative bg-gradient-to-br from-green-900/50 to-green-950/50 backdrop-blur-xl rounded-xl border border-green-500/30 p-4 text-center">
                    <div className="text-3xl font-black text-green-400 mb-1">99.9%</div>
                    <div className="text-xs text-slate-400">Uptime SLA</div>
                  </div>
                </div>
                <div className="relative group">
                  <div className="absolute inset-0 bg-blue-600 rounded-xl blur-lg opacity-30 group-hover:opacity-50 transition-opacity"></div>
                  <div className="relative bg-gradient-to-br from-blue-900/50 to-blue-950/50 backdrop-blur-xl rounded-xl border border-blue-500/30 p-4 text-center">
                    <div className="text-3xl font-black text-blue-400 mb-1">&lt;24h</div>
                    <div className="text-xs text-slate-400">Response Time</div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Contact Form */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-600 to-blue-600 rounded-3xl blur-2xl opacity-30 group-hover:opacity-50 transition-all"></div>
              <div className="relative bg-gradient-to-br from-slate-800/90 to-slate-900/90 backdrop-blur-2xl rounded-3xl border border-purple-500/30 p-8">
                <h3 className="text-3xl font-bold text-white mb-6">Send us a message</h3>
                <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-2">Your Name</label>
                    <input
                      type="text"
                      placeholder="John Doe"
                      className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-2">Email Address</label>
                    <input
                      type="email"
                      placeholder="john@company.com"
                      className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-2">Company</label>
                    <input
                      type="text"
                      placeholder="Your Game Studio"
                      className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:border-pink-500 focus:ring-2 focus:ring-pink-500/20 transition-all outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-slate-300 mb-2">Message</label>
                    <textarea
                      rows={4}
                      placeholder="Tell us about your project and how we can help..."
                      className="w-full px-4 py-3 bg-slate-900/50 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all outline-none resize-none"
                    ></textarea>
                  </div>
                  <button
                    type="submit"
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white font-bold py-4 px-6 rounded-xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl flex items-center justify-center gap-3 group"
                  >
                    <span>Send Message</span>
                    <Send className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </button>
                </form>
                
                {/* Social Links */}
                <div className="mt-8 pt-6 border-t border-slate-700/50">
                  <p className="text-sm text-slate-400 mb-4 text-center">Connect with us</p>
                  <div className="flex items-center justify-center gap-4">
                    <a href="#" className="w-12 h-12 bg-slate-800/50 hover:bg-blue-600/50 rounded-xl flex items-center justify-center transition-all transform hover:scale-110 border border-slate-700 hover:border-blue-500">
                      <Globe className="w-5 h-5 text-slate-400 hover:text-white" />
                    </a>
                    <a href="#" className="w-12 h-12 bg-slate-800/50 hover:bg-purple-600/50 rounded-xl flex items-center justify-center transition-all transform hover:scale-110 border border-slate-700 hover:border-purple-500">
                      <Code2 className="w-5 h-5 text-slate-400 hover:text-white" />
                    </a>
                    <a href="#" className="w-12 h-12 bg-slate-800/50 hover:bg-pink-600/50 rounded-xl flex items-center justify-center transition-all transform hover:scale-110 border border-slate-700 hover:border-pink-500">
                      <Rocket className="w-5 h-5 text-slate-400 hover:text-white" />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Footer with Copyright */}
      <footer className="relative py-12 px-4 border-t border-slate-800/50 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-purple-950/30 to-blue-950/30"></div>
        
        {/* Animated Stars */}
        {[...Array(30)].map((_, i) => (
          <div
            key={i}
            className="absolute w-0.5 h-0.5 bg-white rounded-full animate-star-twinkle"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 3}s`
            }}
          />
        ))}
        
        <div className="max-w-7xl mx-auto relative z-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
            {/* Brand */}
            <div>
              <h3 className="text-2xl font-black text-white mb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                PlayMetric PAIME
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed">
                Revolutionizing mobile game testing through advanced AI agents that learn, play, and optimize gameplay automatically.
              </p>
            </div>
            
            {/* Quick Links */}
            <div>
              <h4 className="text-white font-bold mb-4">Platform</h4>
              <ul className="space-y-2 text-sm text-slate-400">
                <li><a href="#" className="hover:text-purple-400 transition-colors">Dashboard</a></li>
                <li><a href="#" className="hover:text-purple-400 transition-colors">Analytics</a></li>
                <li><a href="#" className="hover:text-purple-400 transition-colors">Game Sessions</a></li>
                <li><a href="#" className="hover:text-purple-400 transition-colors">Documentation</a></li>
              </ul>
            </div>
            
            {/* Technologies */}
            <div>
              <h4 className="text-white font-bold mb-4">Powered By</h4>
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 bg-blue-900/30 text-blue-400 text-xs rounded-full border border-blue-500/30">React</span>
                <span className="px-3 py-1 bg-purple-900/30 text-purple-400 text-xs rounded-full border border-purple-500/30">Python</span>
                <span className="px-3 py-1 bg-pink-900/30 text-pink-400 text-xs rounded-full border border-pink-500/30">Docker</span>
                <span className="px-3 py-1 bg-green-900/30 text-green-400 text-xs rounded-full border border-green-500/30">PostgreSQL</span>
                <span className="px-3 py-1 bg-orange-900/30 text-orange-400 text-xs rounded-full border border-orange-500/30">Redis</span>
                <span className="px-3 py-1 bg-cyan-900/30 text-cyan-400 text-xs rounded-full border border-cyan-500/30">Gemini AI</span>
              </div>
            </div>
          </div>
          
          {/* Copyright Bar */}
          <div className="pt-8 border-t border-slate-800/50">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span>System Operational</span>
              </div>
              
              <div className="text-center">
                <p className="text-slate-400 text-sm">
                  © {new Date().getFullYear()} <span className="text-white font-semibold">PlayMetric PAIME</span>. All rights reserved.
                </p>
                <p className="text-slate-500 text-xs mt-1">
                  Built with 💜 for the future of mobile gaming
                </p>
              </div>
              
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <a href="#" className="hover:text-purple-400 transition-colors">Privacy Policy</a>
                <span>•</span>
                <a href="#" className="hover:text-purple-400 transition-colors">Terms of Service</a>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
