"use client";

import { useEffect, useState } from "react";

interface Star {
  id: number;
  left: string;
  top: string;
  size: number;
  opacity: number;
}

export function StarField() {
  const [stars, setStars] = useState<Star[]>([]);

  useEffect(() => {
    const generatedStars: Star[] = [];
    // Generate many more static stars scattered across the screen
    for (let i = 0; i < 200; i++) {
      generatedStars.push({
        id: i,
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        size: Math.random() * 2 + 0.5,
        opacity: Math.random() * 0.7 + 0.3,
      });
    }
    setStars(generatedStars);
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
      {/* Static star field */}
      {stars.map((star) => (
        <div
          key={star.id}
          className="absolute rounded-full bg-white"
          style={{
            left: star.left,
            top: star.top,
            width: `${star.size}px`,
            height: `${star.size}px`,
            opacity: star.opacity,
          }}
        />
      ))}

      {/* Large soft purple glowing orbs */}
      {/* Top-left orb */}
      <div 
        className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full opacity-40"
        style={{
          background: 'radial-gradient(circle, rgba(155, 93, 229, 0.6) 0%, rgba(123, 47, 190, 0.3) 40%, transparent 70%)',
          filter: 'blur(60px)',
        }}
      />
      
      {/* Bottom-right orb */}
      <div 
        className="absolute -bottom-48 -right-32 w-[600px] h-[600px] rounded-full opacity-50"
        style={{
          background: 'radial-gradient(circle, rgba(155, 93, 229, 0.5) 0%, rgba(123, 47, 190, 0.25) 45%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />

      {/* Additional subtle orb center-right */}
      <div 
        className="absolute top-1/3 -right-20 w-[400px] h-[400px] rounded-full opacity-25"
        style={{
          background: 'radial-gradient(circle, rgba(155, 93, 229, 0.4) 0%, transparent 60%)',
          filter: 'blur(50px)',
        }}
      />
    </div>
  );
}
