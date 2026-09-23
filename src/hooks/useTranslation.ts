import { useAppStore } from '@/store/useAppStore';
import { en } from '@/locales/en';
import { ta } from '@/locales/ta';

export function useTranslation() {
  const lang = useAppStore((state) => state.language);
  const t = (key: string, replacements?: Record<string, string | number>) => {
    const keys = key.split('.');
    let dict: any = lang === 'ta' ? ta : en;
    for (const k of keys) {
      if (dict && dict[k] !== undefined) {
        dict = dict[k];
      } else {
        // Fallback to English key path
        let fallback: any = en;
        for (const fk of keys) {
          if (fallback && fallback[fk] !== undefined) {
            fallback = fallback[fk];
          } else {
            return key; // return key path if not found in English either
          }
        }
        dict = fallback;
        break;
      }
    }

    let translation = String(dict);
    if (replacements) {
      Object.entries(replacements).forEach(([k, v]) => {
        translation = translation.replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), String(v));
      });
    }

    return translation;
  };

  return { t, lang };
}
export type TFunction = ReturnType<typeof useTranslation>['t'];
export type Language = 'en' | 'ta';
