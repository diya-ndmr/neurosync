import { useAccessibility, type Contrast, type Language, type MotionPreference, type TextSize, type Transparency } from '../context/AccessibilityContext';

export default function AccessibilitySettings() {
  const preferences = useAccessibility();
  const { t } = preferences;
  return <div className="mx-auto max-w-3xl space-y-5">
    <header className="border-b border-ns-border pb-4">
      <h1 className="text-2xl font-semibold">{t('preferences.title')}</h1>
      <p className="mt-1 text-sm text-ns-text-secondary">{t('preferences.description')}</p>
    </header>
    <section className="neo-card space-y-5 p-6" aria-labelledby="access-language-title">
      <h2 id="access-language-title" className="font-semibold">{t('preferences.language')}</h2>
      <PreferenceSelect id="language" label={t('preferences.language')} value={preferences.language} onChange={(value) => preferences.setLanguage(value as Language)} options={[
        ['en', 'English'], ['zu', 'isiZulu'], ['xh', 'isiXhosa'], ['af', 'Afrikaans']
      ]} />
      <PreferenceSelect id="text-size" label={t('preferences.textSize')} value={preferences.textSize} onChange={(value) => preferences.setTextSize(value as TextSize)} options={[
        ['default', t('preferences.textDefault')], ['large', t('preferences.textLarge')], ['extra-large', t('preferences.textExtraLarge')]
      ]} />
      <PreferenceSelect id="contrast" label={t('preferences.contrast')} value={preferences.contrast} onChange={(value) => preferences.setContrast(value as Contrast)} options={[
        ['default', t('preferences.contrastDefault')], ['high', t('preferences.contrastHigh')]
      ]} />
      <PreferenceSelect id="motion" label={t('preferences.motion')} value={preferences.motion} onChange={(value) => preferences.setMotion(value as MotionPreference)} options={[
        ['standard', t('preferences.motionStandard')], ['reduced', t('preferences.motionReduced')]
      ]} />
      <PreferenceSelect id="transparency" label={t('preferences.transparency')} value={preferences.transparency} onChange={(value) => preferences.setTransparency(value as Transparency)} options={[
        ['standard', t('preferences.transparencyStandard')], ['reduced', t('preferences.transparencyReduced')]
      ]} />
      <p className="border-t border-ns-divider pt-4 text-sm text-ns-text-secondary">{t('preferences.localStorageNote')}</p>
    </section>
  </div>;
}

function PreferenceSelect({ id, label, value, onChange, options }: { id: string; label: string; value: string; onChange: (value: string) => void; options: [string, string][] }) {
  return <div className="grid gap-2 sm:grid-cols-[minmax(12rem,1fr)_minmax(12rem,1fr)] sm:items-center">
    <label htmlFor={id} className="text-sm font-semibold">{label}</label>
    <select id={id} className="neo-input" value={value} onChange={(event) => onChange(event.target.value)}>{options.map(([optionValue, text]) => <option key={optionValue} value={optionValue}>{text}</option>)}</select>
  </div>;
}