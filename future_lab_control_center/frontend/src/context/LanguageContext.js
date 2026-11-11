import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations, translateBackendText } from '../utils/translations';

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState('en');

  useEffect(() => {
    const saved = localStorage.getItem('future_lab_lang');
    if (saved && (saved === 'pt' || saved === 'en')) {
      setLang(saved);
    }
  }, []);

  const toggleLanguage = (newLang) => {
    const l = newLang || (lang === 'pt' ? 'en' : 'pt');
    setLang(l);
    localStorage.setItem('future_lab_lang', l);
  };

  const t = (key) => {
    return translations[lang]?.[key] || translations['pt']?.[key] || key;
  };

  const tb = (text) => {
    return translateBackendText(text, lang);
  };

  return (
    <LanguageContext.Provider value={{ lang, toggleLanguage, t, tb }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    return {
      lang: 'pt',
      toggleLanguage: () => {},
      t: (key) => translations['pt']?.[key] || key,
      tb: (text) => text
    };
  }
  return context;
};
