export interface LetterContent {
  text: string;
  emotionalMarkers: {
    distress: number;    // 0-1
    longing: number;     // 0-1
    hope: number;        // 0-1
  };
  musicalMapping: {
    baseTempoMultiplier: number;  // How heart rate affects tempo
    intensityThreshold: number;   // When pattern complexity increases
    sectionDurations: {
      entrance: number;
      emotional: number;
      exit: number;
    };
  };
}

export const letters = {
  1: {
    id: '2000-06963-002',
    type: 'daughter-to-mother',
    path: '/letters/2000-06963-002.jpg',
    emotion: 'sadness',
    color: '#3b82f6',
    content: {
      text: "On the 24th, I received fifty Hong Kong dollars at Xichangs. It pains me deeply to know that you have endured such suffering. Father is also injured, and this saddens me greatly. But now, the night has fallen.",
      emotionalMarkers: {
        distress: 0.9,    // High distress about family's suffering
        longing: 0.8,     // Strong desire to help
        hope: 0.3         // Low hope given situation
      },
      musicalMapping: {
        baseTempoMultiplier: 0.8,  // Slower, more contemplative
        intensityThreshold: 85,    // Heart rate threshold for pattern complexity
        sectionDurations: {
          entrance: 8000,  // Longer entrance to establish mood
          emotional: 12000,// Extended emotional section
          exit: 6000      // Gradual fade
        }
      }
    }
  },
  2: {
    id: '2000-06965-002',
    type: 'mother-to-son',
    path: '/letters/2000-06965-002.jpg',
    emotion: 'concern',
    color: '#f59e0b',
    content: {
      text: "Mother, father is very ill, and he hasn't improved at all.",
      emotionalMarkers: {
        distress: 0.7,    // Moderate distress
        longing: 0.6,     // Missing son
        hope: 0.4         // Slight hope for improvement
      },
      musicalMapping: {
        baseTempoMultiplier: 0.9,  // Slightly faster, more urgent
        intensityThreshold: 80,    // Lower threshold for complexity
        sectionDurations: {
          entrance: 6000,  // Shorter entrance
          emotional: 15000,// Longer emotional expression
          exit: 8000      // Extended exit
        }
      }
    }
  }
};
