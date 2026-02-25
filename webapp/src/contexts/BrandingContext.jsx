import { createContext, useContext, useState, useEffect } from 'react'

const BrandingContext = createContext(null)

const DEFAULT_BRANDING = {
  broker_name: 'Griffin Gold',
  primary_color: '#D4AF37',
  secondary_color: '#0f0f14',
  accent_color: '#FFD700',
  logo_url: '',
  bot_name: 'Griffin Gold',
}

export function BrandingProvider({ children }) {
  const [branding, setBranding] = useState(DEFAULT_BRANDING)

  useEffect(() => {
    fetch('/api/branding')
      .then(r => r.json())
      .then(data => {
        setBranding(data)
        // Apply CSS custom properties
        document.documentElement.style.setProperty('--color-primary', data.primary_color)
        document.documentElement.style.setProperty('--color-accent', data.accent_color)
        document.documentElement.style.setProperty('--color-secondary', data.secondary_color)
      })
      .catch(() => {}) // Use defaults on error
  }, [])

  return (
    <BrandingContext.Provider value={branding}>
      {children}
    </BrandingContext.Provider>
  )
}

export function useBranding() {
  return useContext(BrandingContext) || DEFAULT_BRANDING
}
