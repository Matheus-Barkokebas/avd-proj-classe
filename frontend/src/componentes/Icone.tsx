/* Ícones de traço próprio (os mesmos do protótipo v3), sem dependência externa. */

const CAMINHOS = {
  painel: '<rect x="3" y="3" width="7.5" height="9" rx="1.5"/><rect x="13.5" y="3" width="7.5" height="5.5" rx="1.5"/><rect x="13.5" y="11.5" width="7.5" height="9.5" rx="1.5"/><rect x="3" y="15" width="7.5" height="6" rx="1.5"/>',
  mapa: '<path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6 9 4z"/><path d="M9 4v14M15 6v14"/>',
  chuva: '<path d="M7 15.5a4.5 4.5 0 1 1 1.3-8.8A6 6 0 0 1 19.6 9.2a3.4 3.4 0 0 1-1.1 6.3H7z"/><path d="M8.5 18.5 7.5 21M12.5 18.5l-1 2.5M16.5 18.5l-1 2.5"/>',
  pulso: '<path d="M3 12h3.5l2.5-6.5 4 13 2.8-6.5H21"/>',
  sirene: '<path d="M7 18v-6a5 5 0 0 1 10 0v6"/><path d="M5 21h14M12 3v1.5M4.2 6.2l1.1 1.1M19.8 6.2l-1.1 1.1M3 12h1.5M19.5 12H21"/><path d="M10 18v-5.5"/>',
  equipe: '<circle cx="9" cy="8" r="3.4"/><path d="M2.8 20c.8-3.6 3.3-5.6 6.2-5.6s5.4 2 6.2 5.6"/><path d="M16 4.6a3.4 3.4 0 0 1 0 6.8M18.2 14.6c1.8.7 2.8 2.5 3.1 5.4"/>',
  ajustes: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/><path d="M4 12h13M21 12h-1"/>',
  doc: '<path d="M14 3H7a1.5 1.5 0 0 0-1.5 1.5v15A1.5 1.5 0 0 0 7 21h10a1.5 1.5 0 0 0 1.5-1.5V7.5L14 3z"/><path d="M14 3v4.5h4.5M9 12.5h6M9 16h4"/>',
  banco: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5"/>',
  sol: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
  lua: '<path d="M20 14.6A8 8 0 1 1 9.4 4a6.4 6.4 0 0 0 10.6 10.6z"/>',
  recolher: '<path d="m15 6-6 6 6 6"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  dir: '<path d="m9 6 6 6-6 6"/>',
  marca: '<path d="M3.5 18 9.5 7.5l3.4 5.6 2.1-3.1 5.5 8"/><circle cx="16.5" cy="5.5" r="1.6"/>',
  atualizar: '<path d="M20 11a8 8 0 0 0-14.6-3.6M4 4.5v3.8h3.8M4 13a8 8 0 0 0 14.6 3.6M20 19.5v-3.8h-3.8"/>',
  alerta: '<path d="M12 3.5 2.5 20h19L12 3.5z"/><path d="M12 10v4.5M12 17.4v.1"/>',
} as const;

export type NomeIcone = keyof typeof CAMINHOS;

export function Icone({ nome, tamanho = 16, traco = 1.75 }: { nome: NomeIcone; tamanho?: number; traco?: number }) {
  return (
    <svg
      className="ic" width={tamanho} height={tamanho} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={traco} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: CAMINHOS[nome] }}
    />
  );
}
