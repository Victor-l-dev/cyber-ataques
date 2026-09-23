# -*- coding: utf-8 -*-
"""
TECHSECURE S.A. -- SALA DE CONTROLE DE INCIDENTES
Simulacao imersiva em Pygame para dinamicas de conscientizacao em
ciberseguranca. O jogador atua como Analista de Plantao e precisa
investigar CINCO servidores comprometidos, com pistas mais sutis e
pegadinhas no log, antes que o tempo (reduzido) acabe ou a integridade
da rede corporativa chegue a zero.

LAYOUT:
  - HUD SUPERIOR: cronometro regressivo em tempo real + barra de
    Integridade da Rede Corporativa (comeca em 100%).
  - PAINEL ESQUERDO: lista dos servidores afetados (SRV-RH01, SRV-FIN02,
    SRV-PROD03), cada um com um indicador de status.
  - PAINEL DIREITO (Terminal de Auditoria): exibe o log/codigo-fonte
    capturado no servidor selecionado, com pistas sobre o tipo de
    gatilho (Bomba Logica x Bomba Relogio), revelado com efeito de
    maquina de escrever.
  - Apos um diagnostico correto, o analista precisa concluir um mini-jogo
    de reinicio: guiar o pacote "SAVE" por uma trilha de circuito impresso
    (estilo placa de PCB) ate o ponto de destino, desviando dos nos de
    risco (vermelhos), contra um cronometro proprio do hack.

IMPORTANTE: todo o conteudo (logs, codigo) e ficticio e ilustrativo,
criado apenas para fins didaticos. Nao ha codigo malicioso real nem
tecnicas de invasao.

Controles:
  - Mouse: selecionar servidor / clicar em BOMBA LOGICA ou BOMBA RELOGIO
  - Setas do teclado: apos diagnostico correto, guiar o pacote pela
    trilha do circuito ate o ponto SAVE, evitando os nos vermelhos
  - ESPACO: avancar a sequencia de inicializacao / tela final -> reinicio
  - R: reiniciar apos a tela final
  - ESC: sair
"""

import pygame
import random
import sys
import math

pygame.init()

# ---------------------------------------------------------------------------
# Configuracao geral
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1150, 760
FPS = 60

GLOBAL_TIME = 150.0           # tempo total reduzido -- mais dificil
INTEGRITY_START = 100
WRONG_PENALTY = 15
CONNECT_TIME = 1.1           # duracao da animacao de "conectando..."
FEEDBACK_HOLD = 3.2           # segundos mostrando o resultado do diagnostico

MAZE_COLS = 8
MAZE_ROWS = 5
MAZE_HAZARDS = 3
MAZE_TIME = 22.0              # cronometro proprio do hack de reinicio
MAZE_HAZARD_PENALTY = 8
MAZE_TIMEOUT_PENALTY = 12

BG = (5, 7, 11)
PANEL_BG = (13, 17, 26)
TERMINAL_BG = (9, 12, 18)
NEON_CYAN = (60, 230, 220)
NEON_GREEN = (80, 240, 140)
NEON_PINK = (255, 70, 140)
NEON_YELLOW = (250, 220, 90)
NEON_RED = (255, 70, 70)
NEON_PURPLE = (170, 120, 255)
GRID_LINE = (18, 40, 40)
TEXT_MAIN = (208, 238, 233)
TEXT_DIM = (100, 140, 140)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TechSecure S.A. - Sala de Controle de Incidentes")
clock = pygame.time.Clock()
pygame.key.set_repeat(220, 90)

font_logo = pygame.font.SysFont("consolas", 30, bold=True)
font_title = pygame.font.SysFont("consolas", 34, bold=True)
font_h2 = pygame.font.SysFont("consolas", 21, bold=True)
font_body = pygame.font.SysFont("consolas", 17)
font_small = pygame.font.SysFont("consolas", 14)
font_code = pygame.font.SysFont("consolas", 16)
font_clock = pygame.font.SysFont("consolas", 40, bold=True)
font_mono_rain = pygame.font.SysFont("consolas", 16)


# ---------------------------------------------------------------------------
# Chuva digital (fundo atmosferico)
# ---------------------------------------------------------------------------
RAIN_CHARS = "01LOGICATEMPORELOGIOGATILHO$#@%01010101"

class DigitalRain:
    def __init__(self, width, height, font):
        self.font = font
        self.char_w = 15
        self.cols = width // self.char_w
        self.drops = [random.randint(-40, 0) for _ in range(self.cols)]
        self.speeds = [random.uniform(0.25, 0.9) for _ in range(self.cols)]

    def update_and_draw(self, surface, alpha=45):
        fade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade.fill((5, 7, 11, alpha))
        surface.blit(fade, (0, 0))
        for i in range(self.cols):
            ch = random.choice(RAIN_CHARS)
            x = i * self.char_w
            y = int(self.drops[i]) * 17
            glyph = self.font.render(ch, True, (30, 130, 100))
            surface.blit(glyph, (x, y))
            self.drops[i] += self.speeds[i]
            if y > HEIGHT and random.random() > 0.975:
                self.drops[i] = random.randint(-20, 0)


rain = DigitalRain(WIDTH, HEIGHT, font_mono_rain)


def draw_background():
    rain.update_and_draw(screen, alpha=60)
    step = 42
    for x in range(0, WIDTH, step):
        pygame.draw.line(screen, GRID_LINE, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, step):
        pygame.draw.line(screen, GRID_LINE, (0, y), (WIDTH, y), 1)


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------
def draw_text(surface, text, font, color, x, y, center=False):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(x, y)) if center else surf.get_rect(topleft=(x, y))
    surface.blit(surf, rect)
    return rect


def wrap_text(text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] > max_width:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def neon_panel(rect, border_color, bg_color=PANEL_BG, width=2, radius=10):
    pygame.draw.rect(screen, bg_color, rect, border_radius=radius)
    pygame.draw.rect(screen, border_color, rect, width=width, border_radius=radius)


class Typewriter:
    def __init__(self, text="", chars_per_sec=70):
        self.full_text = text
        self.chars_per_sec = chars_per_sec
        self.elapsed = 0.0

    def reset(self, text=None):
        if text is not None:
            self.full_text = text
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt

    def visible_len(self):
        return int(self.elapsed * self.chars_per_sec)

    def done(self):
        return self.visible_len() >= len(self.full_text)


# ---------------------------------------------------------------------------
# Dados dos servidores afetados
# ---------------------------------------------------------------------------
SERVERS = [
    {
        "id": "SRV-RH01",
        "label": "Banco de Dados de RH",
        "type": "LOGICA",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-RH01",
            "[AUDITORIA] Extraindo trigger suspeito da tabela 'funcionarios'...",
            "",
            "-- trigger: after_update ON tabela_funcionarios",
            "-- ultima manutencao registrada: 15/06/2025",
            "IF NEW.status_emprego = 'DEMITIDO' THEN",
            "    EXECUTE limpar_registros_criticos(NEW.id_funcionario);",
            "    EXECUTE revogar_credenciais_admin();",
            "END IF;",
            "",
            "[NOTA DO SISTEMA] A data de manutencao acima e apenas um",
            "                  registro de log, nao faz parte da condicao",
            "                  que ativa o bloco EXECUTE.",
        ],
        "explain": (
            "Correto: e uma BOMBA LOGICA. O trigger so executa quando uma "
            "CONDICAO de negocio se torna verdadeira (status = 'DEMITIDO'). "
            "A data de 'ultima manutencao' no comentario e apenas "
            "metadado de log -- uma pegadinha comum: nem toda data no "
            "codigo e o gatilho real. A logica reage a um ESTADO do "
            "sistema (MITRE ATT&CK T1485)."
        ),
    },
    {
        "id": "SRV-FIN02",
        "label": "Financeiro / Agendador Cron",
        "type": "RELOGIO",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-FIN02",
            "[AUDITORIA] Lendo tarefas agendadas em /etc/cron.d/...",
            "",
            "# /etc/cron.d/maintenance",
            "# executa apenas se o disco tiver espaco livre (checagem de rotina)",
            "0 3 15 6 * root /opt/scripts/cleanup_all.sh --force",
            "",
            "# cleanup_all.sh executa: rm -rf /data/financeiro/* sem confirmacao",
            "",
            "[NOTA DO SISTEMA] A checagem de espaco em disco e uma rotina",
            "                  padrao do cron, nao uma condicao de negocio.",
            "                  O disparo em si depende so do horario agendado.",
        ],
        "explain": (
            "Correto: e uma BOMBA RELOGIO. A entrada de cron dispara em "
            "uma data/hora especifica e fixa (dia 15/06, 03h). O comentario "
            "sobre 'espaco em disco' e uma checagem tecnica de rotina do "
            "sistema operacional, nao uma condicao de negocio -- outra "
            "pegadinha para testar a leitura atenta do log."
        ),
    },
    {
        "id": "SRV-PROD03",
        "label": "Producao (Monitoramento)",
        "type": "LOGICA",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-PROD03",
            "[AUDITORIA] Analisando processo watchdog em segundo plano...",
            "",
            "# roda a cada 24 horas (ciclo do watchdog)",
            "a_cada_24h:",
            "    if dias_desde_ultimo_checkin('analista_producao') > 15:",
            "        liberar_payload_destrutivo()",
            "",
            "[NOTA DO SISTEMA] O watchdog SEMPRE roda a cada 24h -- isso e",
            "                  so a frequencia de verificacao. A condicao",
            "                  real esta dentro do IF: dias sem check-in.",
        ],
        "explain": (
            "Correto: e uma BOMBA LOGICA (variante Dead Man's Switch). "
            "Repare na pegadinha: 'roda a cada 24 horas' descreve apenas a "
            "FREQUENCIA com que o watchdog verifica algo -- o disparo real "
            "acontece pela AUSENCIA de check-in por mais de 15 dias, um "
            "ESTADO do sistema, nao uma data fixa no calendario."
        ),
    },
    {
        "id": "SRV-LIC04",
        "label": "Licenciamento e Integridade",
        "type": "LOGICA",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-LIC04",
            "[AUDITORIA] Verificando modulo de licenciamento...",
            "",
            "def checagem_integridade():",
            "    # licenca emitida em 01/01/2024, validade prevista: 2030",
            "    hash_atual = calcular_hash(binario_core)",
            "    if hash_atual != HASH_ESPERADO:",
            "        travar_producao()",
            "",
            "[NOTA DO SISTEMA] As datas de emissao/validade sao apenas",
            "                  informativas. A funcao so age se o HASH",
            "                  do binario for alterado.",
        ],
        "explain": (
            "Correto: e uma BOMBA LOGICA. Apesar de o comentario mostrar "
            "datas de emissao e validade, a condicao real do IF compara "
            "HASHES -- ou seja, dispara quando o binario e alterado (um "
            "ESTADO de integridade), nao em uma data especifica. Padrao "
            "associado a retaliacao contra auditorias ou patches."
        ),
    },
    {
        "id": "SRV-NTP05",
        "label": "Sincronizacao de Horario (NTP)",
        "type": "RELOGIO",
        "log": [
            "[AUDITORIA] Conexao estabelecida com SRV-NTP05",
            "[AUDITORIA] Inspecionando processo de sincronizacao...",
            "",
            "# usuario_atual = 'admin' (sessao ativa no momento da captura)",
            "while True:",
            "    if system_clock.now() >= datetime(2026, 12, 31, 23, 59):",
            "        corromper_backup_incremental()",
            "    sleep(3600)",
            "",
            "[NOTA DO SISTEMA] O comentario sobre o usuario 'admin' e so",
            "                  informacao de sessao, nao faz parte da",
            "                  condicao do IF.",
        ],
        "explain": (
            "Correto: e uma BOMBA RELOGIO. O comentario sobre o usuario "
            "'admin' logado e apenas contexto da captura de tela do log -- "
            "irrelevante para o gatilho. A condicao real compara o relogio "
            "do sistema com uma data-alvo fixa (31/12/2026), uma "
            "assinatura classica de gatilho temporal."
        ),
    },
]


# ---------------------------------------------------------------------------
# Sequencia de inicializacao (boot) -- imersao
# ---------------------------------------------------------------------------
BOOT_LINES = [
    "INICIANDO PROTOCOLO DE CONTENCAO TECHSECURE...",
    "CARREGANDO INVENTARIO DE SERVIDORES AFETADOS...",
    "SINCRONIZANDO RELOGIO DE AUDITORIA...",
    "ESTABELECENDO CANAL SEGURO COM O SOC...",
    "5 INCIDENTES ATIVOS DETECTADOS.",
    "INTEGRIDADE DA REDE CORPORATIVA: 100%",
    "AGUARDANDO ANALISTA DE PLANTAO...",
]


# ---------------------------------------------------------------------------
# Mini-jogo de reinicio -- trilha de circuito (estilo hack do Fleeca, GTA V)
# ---------------------------------------------------------------------------
MAZE_DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
MAZE_OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def generate_maze(cols, rows):
    walls = [[{"N": True, "S": True, "E": True, "W": True} for _ in range(rows)] for _ in range(cols)]
    visited = [[False] * rows for _ in range(cols)]
    start_stack = [(0, 0)]
    visited[0][0] = True
    while start_stack:
        cx, cy = start_stack[-1]
        options = []
        for d, (dx, dy) in MAZE_DIRS.items():
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cols and 0 <= ny < rows and not visited[nx][ny]:
                options.append((d, nx, ny))
        if options:
            d, nx, ny = random.choice(options)
            walls[cx][cy][d] = False
            walls[nx][ny][MAZE_OPPOSITE[d]] = False
            visited[nx][ny] = True
            start_stack.append((nx, ny))
        else:
            start_stack.pop()
    return walls


def maze_dead_ends(walls, cols, rows, exclude):
    ends = []
    for x in range(cols):
        for y in range(rows):
            if (x, y) in exclude:
                continue
            open_dirs = sum(1 for d in MAZE_DIRS if not walls[x][y][d])
            if open_dirs == 1:
                ends.append((x, y))
    return ends


class MazeHack:
    def __init__(self, cols=MAZE_COLS, rows=MAZE_ROWS, hazards=MAZE_HAZARDS):
        self.cols = cols
        self.rows = rows
        self.walls = generate_maze(cols, rows)
        self.start = (0, rows - 1)
        self.end = (cols - 1, 0)
        candidates = maze_dead_ends(self.walls, cols, rows, {self.start, self.end})
        random.shuffle(candidates)
        self.hazards = set(candidates[:hazards])
        self.pos = self.start
        self.trail = [self.start]
        self.time_left = MAZE_TIME

    def move(self, direction):
        dx, dy = MAZE_DIRS[direction]
        cx, cy = self.pos
        if self.walls[cx][cy][direction]:
            return "blocked"
        nx, ny = cx + dx, cy + dy
        self.pos = (nx, ny)
        if self.pos in self.hazards:
            self.pos = self.start
            self.trail = [self.start]
            return "hazard"
        self.trail.append(self.pos)
        if self.pos == self.end:
            return "done"
        return "moved"


# ---------------------------------------------------------------------------
# Estado do jogo
# ---------------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.status = "boot"          # boot, hub, connecting, analyzing, feedback, restart_prompt, gameover, victory
        self.boot_index = 0
        self.boot_timer = 0.0
        self.time_left = GLOBAL_TIME
        self.integrity = INTEGRITY_START
        self.servers = [dict(s, state="pendente", attempts=0) for s in SERVERS]
        self.selected = None
        self.connect_timer = 0.0
        self.log_tw = Typewriter()
        self.last_correct = None
        self.last_explain = ""
        self.feedback_timer = 0.0
        self.mistakes = 0
        self.glitch_timer = 0.0
        self.maze = None
        self.maze_message = ""
        self.maze_message_timer = 0.0

    def secured_count(self):
        return sum(1 for s in self.servers if s["state"] == "secured")

    def select_server(self, index):
        if self.status not in ("hub",):
            return
        self.selected = index
        self.status = "connecting"
        self.connect_timer = 0.0

    def submit_diagnosis(self, kind):
        if self.status != "analyzing" or self.selected is None:
            return
        srv = self.servers[self.selected]
        correct = kind == srv["type"]
        srv["attempts"] += 1
        if correct:
            srv["state"] = "diagnosed"
            self.last_correct = True
        else:
            self.integrity -= WRONG_PENALTY
            self.mistakes += 1
            self.last_correct = False
            self.glitch_timer = 0.5
        self.last_explain = srv["explain"]
        self.status = "feedback"
        self.feedback_timer = FEEDBACK_HOLD

    def start_maze(self):
        self.maze = MazeHack()
        self.maze_message = ""
        self.maze_message_timer = 0.0

    def maze_move(self, direction):
        if self.status != "restart_prompt" or self.maze is None:
            return
        result = self.maze.move(direction)
        if result == "hazard":
            self.integrity -= MAZE_HAZARD_PENALTY
            self.maze_message = "NO DE RISCO ATINGIDO -- pacote reenviado ao inicio."
            self.maze_message_timer = 2.0
            self.glitch_timer = 0.3
        elif result == "done":
            srv = self.servers[self.selected]
            srv["state"] = "secured"
            self.maze = None
            self.back_to_hub_or_end()

    def back_to_hub_or_end(self):
        if self.integrity <= 0:
            self.status = "gameover"
            return
        if self.secured_count() >= len(self.servers):
            self.status = "victory"
            return
        self.status = "hub"
        self.selected = None

    def update(self, dt):
        if self.status == "boot":
            self.boot_timer += dt
            if self.boot_timer > 0.45:
                self.boot_timer = 0.0
                if self.boot_index < len(BOOT_LINES):
                    self.boot_index += 1
        elif self.status in ("hub", "connecting", "analyzing", "feedback", "restart_prompt"):
            self.time_left -= dt
            if self.glitch_timer > 0:
                self.glitch_timer -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.status = "gameover"
                return
            if self.integrity <= 0:
                self.status = "gameover"
                return

            if self.status == "connecting":
                self.connect_timer += dt
                if self.connect_timer >= CONNECT_TIME:
                    self.status = "analyzing"
                    srv = self.servers[self.selected]
                    self.log_tw.reset("\n".join(srv["log"]))
            elif self.status == "analyzing":
                self.log_tw.update(dt)
            elif self.status == "feedback":
                self.feedback_timer -= dt
                if self.feedback_timer <= 0:
                    if self.last_correct:
                        self.status = "restart_prompt"
                        self.start_maze()
                    else:
                        self.back_to_hub_or_end()
            elif self.status == "restart_prompt":
                if self.maze_message_timer > 0:
                    self.maze_message_timer -= dt
                    if self.maze_message_timer <= 0:
                        self.maze_message = ""
                self.maze.time_left -= dt
                if self.maze.time_left <= 0:
                    self.integrity -= MAZE_TIMEOUT_PENALTY
                    self.mistakes += 1
                    self.glitch_timer = 0.5
                    self.maze = None
                    self.back_to_hub_or_end()


state = GameState()


# ---------------------------------------------------------------------------
# Desenho -- HUD
# ---------------------------------------------------------------------------
def draw_hud():
    danger_time = state.time_left < 30
    danger_integrity = state.integrity < 30

    hud_rect = pygame.Rect(0, 0, WIDTH, 108)
    pygame.draw.rect(screen, (9, 11, 17), hud_rect)
    pygame.draw.line(screen, NEON_CYAN, (0, 108), (WIDTH, 108), 2)

    draw_text(screen, "TECHSECURE S.A. -- SALA DE CONTROLE DE INCIDENTES",
              font_logo, NEON_CYAN, 24, 14)
    draw_text(screen, f"Servidores neutralizados: {state.secured_count()}/{len(state.servers)}   |   Falhas: {state.mistakes}",
              font_small, TEXT_DIM, 24, 50)

    # Cronometro
    mins = int(state.time_left) // 60
    secs = int(state.time_left) % 60
    tcolor = NEON_RED if danger_time else NEON_GREEN
    if danger_time and int(state.time_left * 2) % 2 == 0:
        tcolor = (255, 255, 255)
    draw_text(screen, "TEMPO RESTANTE", font_small, TEXT_DIM, WIDTH - 260, 16)
    draw_text(screen, f"{mins:02d}:{secs:02d}", font_clock, tcolor, WIDTH - 260, 40)

    # Barra de integridade
    bar_x, bar_y, bar_w, bar_h = 24, 76, WIDTH - 320, 22
    draw_text(screen, "INTEGRIDADE DA REDE CORPORATIVA", font_small, TEXT_DIM, bar_x, bar_y - 16)
    pygame.draw.rect(screen, (25, 25, 25), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    ratio = max(0, state.integrity) / INTEGRITY_START
    icolor = NEON_GREEN if ratio > 0.5 else (NEON_YELLOW if ratio > 0.25 else NEON_RED)
    pygame.draw.rect(screen, icolor, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=6)
    pygame.draw.rect(screen, icolor, (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=6)
    draw_text(screen, f"{max(0, state.integrity)}%", font_small, TEXT_MAIN, bar_x + bar_w + 10, bar_y + 2)

    if danger_time or danger_integrity:
        pulse = (math.sin(pygame.time.get_ticks() / 150) + 1) / 2
        alpha = int(30 + pulse * 40)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 0, 0, alpha))
        screen.blit(overlay, (0, 0))


STATUS_COLORS = {
    "pendente": TEXT_DIM,
    "diagnosed": NEON_YELLOW,
    "secured": NEON_GREEN,
    "compromised": NEON_RED,
}
STATUS_LABELS = {
    "pendente": "NAO ANALISADO",
    "diagnosed": "AGUARDANDO COMANDO",
    "secured": "NEUTRALIZADO",
    "compromised": "TENTATIVA FALHOU",
}


def server_status_key(srv):
    if srv["state"] == "secured":
        return "secured"
    if srv["state"] == "diagnosed":
        return "diagnosed"
    if srv["attempts"] > 0:
        return "compromised"
    return "pendente"


def draw_server_list():
    panel = pygame.Rect(20, 128, 330, HEIGHT - 160)
    neon_panel(panel, NEON_PINK)
    draw_text(screen, "SERVIDORES AFETADOS", font_h2, NEON_PINK, panel.x + 16, panel.y + 14)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 16, panel.y + 44), (panel.right - 16, panel.y + 44), 1)

    y = panel.y + 54
    card_h = 68
    for i, srv in enumerate(state.servers):
        rect = pygame.Rect(panel.x + 14, y, panel.width - 28, card_h)
        selected = (state.selected == i and state.status in ("connecting", "analyzing", "feedback", "restart_prompt"))
        status_key = server_status_key(srv)
        border = NEON_YELLOW if selected else STATUS_COLORS.get(status_key, TEXT_DIM)
        neon_panel(rect, border, bg_color=(16, 18, 26), width=2, radius=8)

        dot_color = STATUS_COLORS.get(status_key, TEXT_DIM)
        pygame.draw.circle(screen, dot_color, (rect.x + 16, rect.y + 18), 6)

        draw_text(screen, srv["id"], font_small, NEON_CYAN, rect.x + 30, rect.y + 8)
        label_lines = wrap_text(srv["label"], font_small, rect.width - 42)
        draw_text(screen, label_lines[0] if label_lines else "", font_small, TEXT_MAIN, rect.x + 30, rect.y + 26)

        draw_text(screen, STATUS_LABELS[status_key], font_small, STATUS_COLORS[status_key],
                  rect.x + 30, rect.bottom - 18)

        y += card_h + 8


# ---------------------------------------------------------------------------
# Painel direito -- terminal de auditoria
# ---------------------------------------------------------------------------
def diagnosis_button_rects(panel):
    w, h = 260, 56
    gap = 30
    y = panel.bottom - 90
    x1 = panel.centerx - w - gap // 2
    x2 = panel.centerx + gap // 2
    return {
        "LOGICA": pygame.Rect(x1, y, w, h),
        "RELOGIO": pygame.Rect(x2, y, w, h),
    }


def draw_terminal_idle(panel):
    draw_text(screen, "TERMINAL DE AUDITORIA", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)
    draw_text(screen, "Selecione um servidor na lista a esquerda para iniciar a", font_body, TEXT_DIM,
              panel.x + 20, panel.y + 80)
    draw_text(screen, "captura e analise do log de auditoria.", font_body, TEXT_DIM,
              panel.x + 20, panel.y + 104)
    if int(pygame.time.get_ticks() / 500) % 2 == 0:
        draw_text(screen, "_", font_body, NEON_GREEN, panel.x + 20, panel.y + 140)


def draw_terminal_connecting(panel):
    srv = state.servers[state.selected]
    draw_text(screen, "TERMINAL DE AUDITORIA", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    dots = "." * (1 + int(state.connect_timer * 4) % 3)
    draw_text(screen, f"CONECTANDO A {srv['id']}{dots}", font_body, NEON_YELLOW, panel.x + 20, panel.y + 90)

    bar_x, bar_y, bar_w, bar_h = panel.x + 20, panel.y + 130, panel.width - 40, 18
    pygame.draw.rect(screen, (25, 25, 25), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
    prog = min(1.0, state.connect_timer / CONNECT_TIME)
    pygame.draw.rect(screen, NEON_CYAN, (bar_x, bar_y, int(bar_w * prog), bar_h), border_radius=6)
    pygame.draw.rect(screen, NEON_CYAN, (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=6)


def draw_terminal_analyzing(panel):
    srv = state.servers[state.selected]
    draw_text(screen, f"TERMINAL DE AUDITORIA -- {srv['id']}", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    full = state.log_tw.full_text
    visible = full[:state.log_tw.visible_len()]
    lines = visible.split("\n")

    y = panel.y + 58
    for line in lines:
        if line.startswith("[PISTA]") or line.startswith("        "):
            color = NEON_YELLOW
        elif line.startswith("[AUDITORIA]"):
            color = NEON_PURPLE
        elif line.strip().startswith(("#", "--")):
            color = NEON_CYAN
        elif line.strip() == "":
            color = TEXT_DIM
        else:
            color = NEON_GREEN
        draw_text(screen, line, font_code, color, panel.x + 22, y)
        y += 21

    if not state.log_tw.done() and int(pygame.time.get_ticks() / 300) % 2 == 0:
        draw_text(screen, "_", font_code, NEON_GREEN, panel.x + 22, y)

    draw_text(screen, "Classifique o gatilho identificado:", font_body, TEXT_MAIN,
              panel.x + 20, panel.bottom - 130)

    buttons = diagnosis_button_rects(panel)
    labels = {"LOGICA": "BOMBA LOGICA (gatilho de estado)", "RELOGIO": "BOMBA RELOGIO (gatilho temporal)"}
    colors = {"LOGICA": NEON_PINK, "RELOGIO": NEON_CYAN}
    for kind, rect in buttons.items():
        neon_panel(rect, colors[kind], bg_color=(16, 18, 26), width=3, radius=8)
        draw_text(screen, labels[kind], font_body, colors[kind], rect.centerx, rect.centery, center=True)


def draw_terminal_feedback(panel):
    srv = state.servers[state.selected]
    color = NEON_GREEN if state.last_correct else NEON_RED
    title = "DIAGNOSTICO CORRETO -- AMEACA NEUTRALIZADA" if state.last_correct else "DIAGNOSTICO INCORRETO -- INTEGRIDADE REDUZIDA"
    draw_text(screen, f"TERMINAL DE AUDITORIA -- {srv['id']}", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    draw_text(screen, title, font_body, color, panel.x + 20, panel.y + 66)
    y = panel.y + 100
    for line in wrap_text(state.last_explain, font_body, panel.width - 44):
        draw_text(screen, line, font_body, TEXT_MAIN, panel.x + 22, y)
        y += 25

    draw_text(screen, f"Retornando a lista de servidores em {max(0, state.feedback_timer):.1f}s...",
              font_small, TEXT_DIM, panel.x + 20, panel.bottom - 30)


def draw_terminal_restart(panel):
    srv = state.servers[state.selected]
    maze = state.maze
    draw_text(screen, f"TERMINAL DE AUDITORIA -- {srv['id']}", font_h2, NEON_CYAN, panel.x + 20, panel.y + 16)
    pygame.draw.line(screen, GRID_LINE, (panel.x + 20, panel.y + 46), (panel.right - 20, panel.y + 46), 1)

    draw_text(screen, "AMEACA CLASSIFICADA -- REINICIE O SERVIDOR", font_body, NEON_GREEN,
              panel.x + 20, panel.y + 62)
    draw_text(screen, "Use as SETAS para levar o pacote SAVE ate o destino, evitando os nos vermelhos.",
              font_small, TEXT_MAIN, panel.x + 20, panel.y + 88)

    danger = maze.time_left < 6
    tcolor = NEON_RED if danger else NEON_YELLOW
    draw_text(screen, f"TEMPO DO HACK: {max(0, maze.time_left):.1f}s", font_body, tcolor,
              panel.right - 220, panel.y + 62)

    if state.maze_message:
        draw_text(screen, state.maze_message, font_small, NEON_RED, panel.x + 20, panel.y + 110)

    grid_top = panel.y + 132
    grid_area = pygame.Rect(panel.x + 20, grid_top, panel.width - 40, panel.bottom - grid_top - 16)
    cell = min(grid_area.width // maze.cols, grid_area.height // maze.rows)
    maze_w, maze_h = cell * maze.cols, cell * maze.rows
    ox = grid_area.x + (grid_area.width - maze_w) // 2
    oy = grid_area.y + (grid_area.height - maze_h) // 2

    def center(cx, cy):
        return (ox + cx * cell + cell // 2, oy + cy * cell + cell // 2)

    for dx in range(maze.cols + 1):
        x = ox + dx * cell
        pygame.draw.line(screen, GRID_LINE, (x, oy), (x, oy + maze_h), 1)
    for dy in range(maze.rows + 1):
        y = oy + dy * cell
        pygame.draw.line(screen, GRID_LINE, (ox, y), (ox + maze_w, y), 1)

    trace_color = (30, 110, 90)
    for cx in range(maze.cols):
        for cy in range(maze.rows):
            if not maze.walls[cx][cy]["E"] and cx + 1 < maze.cols:
                pygame.draw.line(screen, trace_color, center(cx, cy), center(cx + 1, cy), 5)
            if not maze.walls[cx][cy]["S"] and cy + 1 < maze.rows:
                pygame.draw.line(screen, trace_color, center(cx, cy), center(cx, cy + 1), 5)

    for i in range(len(maze.trail) - 1):
        pygame.draw.line(screen, NEON_CYAN, center(*maze.trail[i]), center(*maze.trail[i + 1]), 7)

    for hx, hy in maze.hazards:
        hc = center(hx, hy)
        pulse = 4 + int(2 * math.sin(pygame.time.get_ticks() / 150))
        pygame.draw.circle(screen, NEON_RED, hc, cell // 5 + pulse, width=0)
        pygame.draw.circle(screen, BG, hc, cell // 6, width=0)

    end_rect = pygame.Rect(0, 0, cell - 10, cell // 2)
    end_rect.center = center(*maze.end)
    neon_panel(end_rect, NEON_PINK, bg_color=(40, 14, 30), width=2, radius=4)
    draw_text(screen, "SAVE", font_small, NEON_PINK, end_rect.centerx, end_rect.centery, center=True)

    start_rect = pygame.Rect(0, 0, cell - 10, cell // 2)
    start_rect.center = center(*maze.start)
    neon_panel(start_rect, TEXT_DIM, bg_color=(20, 24, 30), width=1, radius=4)

    player_c = center(*maze.pos)
    pulse = 3 + int(2 * math.sin(pygame.time.get_ticks() / 120))
    pygame.draw.circle(screen, NEON_YELLOW, player_c, cell // 4 + pulse)
    pygame.draw.circle(screen, BG, player_c, cell // 6)


def draw_hub_or_playing():
    draw_background()
    if state.glitch_timer > 0:
        glitch = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        glitch.fill((255, 0, 60, 25))
        screen.blit(glitch, (random.randint(-6, 6), random.randint(-4, 4)))

    draw_server_list()

    panel = pygame.Rect(368, 128, WIDTH - 388, HEIGHT - 160)
    neon_panel(panel, NEON_CYAN, bg_color=TERMINAL_BG)

    if state.status == "hub":
        draw_terminal_idle(panel)
    elif state.status == "connecting":
        draw_terminal_connecting(panel)
    elif state.status == "analyzing":
        draw_terminal_analyzing(panel)
    elif state.status == "feedback":
        draw_terminal_feedback(panel)
    elif state.status == "restart_prompt":
        draw_terminal_restart(panel)

    draw_hud()
    draw_text(screen, "ESC para sair", font_small, TEXT_DIM, WIDTH // 2, HEIGHT - 14, center=True)


# ---------------------------------------------------------------------------
# Boot / telas finais
# ---------------------------------------------------------------------------
def draw_boot():
    screen.fill(BG)
    rain.update_and_draw(screen, alpha=70)
    draw_text(screen, "TECHSECURE S.A. -- NUCLEO DE SEGURANCA", font_title, NEON_GREEN, WIDTH // 2, 200, center=True)

    y = 280
    for i in range(min(state.boot_index, len(BOOT_LINES))):
        draw_text(screen, f"> {BOOT_LINES[i]}", font_body, NEON_GREEN, WIDTH // 2 - 320, y)
        y += 34

    if state.boot_index >= len(BOOT_LINES):
        if int(pygame.time.get_ticks() / 400) % 2 == 0:
            draw_text(screen, "PRESSIONE ESPACO PARA INICIAR A AUDITORIA", font_h2, NEON_YELLOW,
                      WIDTH // 2, y + 40, center=True)


def draw_end_screen():
    draw_background()
    victory = state.status == "victory"
    title = "TODOS OS SERVIDORES NEUTRALIZADOS" if victory else "PROTOCOLO DE EMERGENCIA ACIONADO"
    sub = "A rede corporativa foi protegida a tempo." if victory else (
        "Tempo esgotado ou integridade da rede zerada." if not victory else "")
    color = NEON_GREEN if victory else NEON_RED

    draw_text(screen, title, font_title, color, WIDTH // 2, 76, center=True)
    draw_text(screen, sub, font_small, TEXT_DIM, WIDTH // 2, 108, center=True)

    draw_text(screen, f"Servidores neutralizados: {state.secured_count()}/{len(state.servers)}"
                       f"   |   Falhas: {state.mistakes}   |   Integridade final: {max(0, state.integrity)}%",
              font_body, NEON_YELLOW, WIDTH // 2, 138, center=True)

    panel = pygame.Rect(90, 168, WIDTH - 180, HEIGHT - 210)
    neon_panel(panel, NEON_CYAN)
    draw_text(screen, "RESUMO TECNICO DOS INCIDENTES:", font_body, TEXT_MAIN, panel.x + 20, panel.y + 12)
    y = panel.y + 42
    for srv in state.servers:
        result = "NEUTRALIZADO" if srv["state"] == "secured" else "NAO RESOLVIDO"
        rcolor = NEON_GREEN if srv["state"] == "secured" else NEON_RED
        tipo = "Bomba Logica" if srv["type"] == "LOGICA" else "Bomba Relogio"
        draw_text(screen, f"{srv['id']} ({srv['label']}) -- {result}  |  Classificacao correta: {tipo}",
                  font_small, rcolor, panel.x + 20, y)
        y += 21

    draw_text(screen, "Pressione R para reiniciar  |  ESC para sair", font_small, TEXT_DIM,
              WIDTH // 2, HEIGHT - 16, center=True)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
def main():
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and state.status == "boot" and state.boot_index >= len(BOOT_LINES):
                    state.status = "hub"
                elif event.key == pygame.K_r and state.status in ("gameover", "victory"):
                    state.reset()
                elif state.status == "restart_prompt":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        state.maze_move("N")
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state.maze_move("S")
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        state.maze_move("W")
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        state.maze_move("E")
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.status == "hub":
                    panel = pygame.Rect(20, 128, 330, HEIGHT - 160)
                    y = panel.y + 54
                    card_h = 68
                    for i in range(len(state.servers)):
                        rect = pygame.Rect(panel.x + 14, y, panel.width - 28, card_h)
                        if rect.collidepoint(event.pos) and state.servers[i]["state"] != "secured":
                            state.select_server(i)
                            break
                        y += card_h + 8
                elif state.status == "analyzing":
                    panel = pygame.Rect(368, 128, WIDTH - 388, HEIGHT - 160)
                    for kind, rect in diagnosis_button_rects(panel).items():
                        if rect.collidepoint(event.pos):
                            state.submit_diagnosis(kind)
                            break

        state.update(dt)

        if state.status == "boot":
            draw_boot()
        elif state.status in ("hub", "connecting", "analyzing", "feedback", "restart_prompt"):
            draw_hub_or_playing()
        elif state.status in ("gameover", "victory"):
            draw_end_screen()

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
