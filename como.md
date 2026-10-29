# Como preencher o /configure do Comet A71

Objetivo: **PT-BR primeiro**; se não houver, **Inglês**; para animes, também **Japonês** (com legenda).

Página: https://a71comet.duckdns.org/configure

---

## Serviços Debrid
| Campo | Valor |
| :--- | :--- |
| Serviço | **Real-Debrid** + sua chave de https://real-debrid.com/apitoken |
| Habilitar Modo Torrent | ❌ desligado (só Real-Debrid, sem P2P) |
| Remover Streams Duplicados | ❌ desligado (só um serviço Debrid, não faz diferença) |
| Buscar Torrents da Conta Debrid | ✅ ligado (mostra o que você já tem na sua conta RD) |

## Resoluções e tamanho
| Campo | Valor |
| :--- | :--- |
| Resoluções | **4K, 1080p, 720p** (tire o 4K se sua TV não for 4K — ver nota abaixo) |
| Máx. de resultados por resolução | **10** (0 = sem limite, lista fica enorme) |
| Tamanho máximo (GB) | **0** (sem limite) |

## Idiomas ⭐ (a parte mais importante)
| Campo | Valor | Por quê |
| :--- | :--- | :--- |
| **Idiomas Obrigatórios** | **VAZIO** ⚠️ | Se puser Português aqui, tudo que for só em Inglês/Japonês **some**. Isso mataria o fallback. |
| **Idiomas Preferidos** | **Português** | Dá bônus de pontuação: o dublado/dual áudio sobe para o topo. |
| **Idiomas Permitidos** | **Português, Inglês, Japonês** | Garante que esses nunca sejam removidos pelos Excluídos. |
| **Idiomas Excluídos** | **Russo, Ucraniano, Hindi, Tâmil, Telugu, Espanhol, Latino, Francês, Italiano, Alemão, Turco, Polonês** | Tira a poluição (dublagens que você não quer). Um release **dual** (ex.: Espanhol + Inglês) continua aparecendo, porque tem um idioma Permitido. |
| Permitir Inglês nos Idiomas | ✅ ligado | Reforço para o Inglês nunca ser barrado. |
| Remover Idiomas Desconhecidos | ❌ **desligado** ⚠️ | A maioria dos releases em inglês não escreve o idioma no nome do arquivo. Ligar isso esconderia muitos deles. |

## Avançado
| Campo | Valor |
| :--- | :--- |
| Pontuação mínima | manter o padrão |
| Mostrar Somente em Cache | ❌ **desligado** ⚠️ (o Comet só sabe o que está em cache via base coletiva do StremThru, que quase não conhece releases brasileiros — ligado, os dublados somem. Os ⚡ continuam aparecendo primeiro) |
| Ordenar Cache e Sem Cache Juntos | ❌ desligado |
| Remover Lixo | ✅ **ligado** ⚠️ (se desligar, **nenhum filtro de idioma é aplicado**) |
| Formato do Resultado | à vontade; deixe "Idiomas" visível para ver as bandeiras 🇧🇷 |

Depois: **Instalar** (ou **Copiar Link** e colar no Stremio da TV/celular).

---

## Como a ordem fica no Stremio
O Comet agrupa por **resolução primeiro** e, dentro de cada resolução, ordena pela pontuação (onde o Português ganha bônus). Ou seja:

```
4K    → PT-BR/dual primeiro, depois EN/JA
1080p → PT-BR/dual primeiro, depois EN/JA
720p  → ...
```

Um dublado em 1080p aparece **abaixo** de um 4K só em inglês. Se você prefere sempre o dublado no topo, desmarque o 4K.

## Animes
O Nyaa (fonte de animes) já está ativo no servidor. Releases japoneses com legenda aparecem porque Japonês está em Permitidos; os dublados/dual PT-BR continuam subindo para o topo. Para mais anime dublado, mantenha também o addon **Animes BR** no Stremio.
