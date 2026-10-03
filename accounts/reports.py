"""PDF productivity report (weekly or monthly) built with ReportLab."""
import math
from collections import Counter, defaultdict
from datetime import timedelta
from io import BytesIO
from xml.sax.saxutils import escape

from django.db.models import Count, Q, Sum
from django.utils import dateformat, timezone

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Circle, Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from goals.models import Goal, Milestone
from habits.models import Habit, HabitLog
from pomodoro.models import PomodoroSession
from study.models import StudySession
from tasks.models import Task

NAVY = colors.HexColor('#0f172a')
INK = colors.HexColor('#111827')
TEXT = colors.HexColor('#374151')
MUTED = colors.HexColor('#6b7280')
FAINT = colors.HexColor('#9ca3af')
LINE = colors.HexColor('#e5e7eb')
SOFT = colors.HexColor('#f8fafc')
AMBER = colors.HexColor('#f59e0b')
AMBER_SOFT = colors.HexColor('#fff7e6')
BLUE = colors.HexColor('#3b82f6')
GREEN = colors.HexColor('#16a34a')
RED = colors.HexColor('#dc2626')

MAX_TASK_ROWS = 7
MAX_HABITS = 6
MAX_GOALS = 5
PRIORITY_COLORS = {'HIGH': RED, 'MEDIUM': AMBER, 'LOW': GREEN}


def style(name, **kwargs):
    base = {'fontName': 'Helvetica', 'fontSize': 9, 'leading': 12, 'textColor': TEXT}
    base.update(kwargs)
    return ParagraphStyle(name, **base)


STYLES = {
    'brand': style('brand', fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.white),
    'eyebrow': style('eyebrow', fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=AMBER),
    'header_right': style('header_right', fontSize=8.5, leading=12, textColor=colors.HexColor('#cbd5e1'), alignment=TA_RIGHT),
    'header_name': style('header_name', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.white, alignment=TA_RIGHT),
    'section': style('section', fontName='Helvetica-Bold', fontSize=10.5, leading=14, textColor=INK, spaceBefore=10, spaceAfter=5),
    'card_label': style('card_label', fontName='Helvetica-Bold', fontSize=6.8, leading=9, textColor=MUTED),
    'card_value': style('card_value', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK),
    'card_value_muted': style('card_value_muted', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=FAINT),
    'card_note': style('card_note', fontSize=7, leading=9, textColor=MUTED),
    'body': style('body'),
    'small': style('small', fontSize=7.5, leading=10, textColor=MUTED),
    'cell': style('cell', fontSize=8.5, leading=11),
    'cell_head': style('cell_head', fontName='Helvetica-Bold', fontSize=7, leading=9, textColor=MUTED),
    'empty': style('empty', fontSize=8.5, leading=12, textColor=MUTED),
    'bullet': style('bullet', fontSize=8.8, leading=13, leftIndent=10, bulletIndent=0),
}


# ---------------------------------------------------------------- formatting

def fmt_day(day):
    return f'{day:%b} {day.day}'


def fmt_minutes(minutes):
    minutes = int(round(minutes))
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f'{rest}m'
    return f'{hours}h {rest}m' if rest else f'{hours}h'


def plural(count, word, suffix='s'):
    return f'{count} {word}{"" if count == 1 else suffix}'


def delta_note(current, previous, compare_label, minutes=False):
    if current == 0 and previous == 0:
        return 'No activity yet', MUTED
    diff = current - previous
    if diff == 0:
        return f'Same as {compare_label}', MUTED
    amount = fmt_minutes(abs(diff)) if minutes else abs(diff)
    return (f'+{amount} vs {compare_label}', GREEN) if diff > 0 else (f'-{amount} vs {compare_label}', RED)


# ---------------------------------------------------------------- data

def period_bounds(period, today):
    """Return (start, period_end, previous_start, previous_end, label, compare_label)."""
    if period == 'monthly':
        start = today.replace(day=1)
        next_month = (start + timedelta(days=32)).replace(day=1)
        period_end = next_month - timedelta(days=1)
        previous_last = start - timedelta(days=1)
        previous_start = previous_last.replace(day=1)
        previous_end = previous_start.replace(day=min(today.day, previous_last.day))
        return start, period_end, previous_start, previous_end, today.strftime('%B %Y'), 'last month'
    start = today - timedelta(days=today.weekday())
    label = f'{fmt_day(start)} – {fmt_day(today)}, {today.year}'
    return start, start + timedelta(days=6), start - timedelta(days=7), today - timedelta(days=7), label, 'last week'


def focus_minutes_by_day(user, start, end):
    totals = defaultdict(float)
    sessions = PomodoroSession.objects.filter(
        user=user, status='COMPLETED', completed_at__date__range=(start, end),
    ).only('completed_at', 'actual_focus_seconds', 'duration_minutes')
    for session in sessions:
        seconds = session.actual_focus_seconds or session.duration_minutes * 60
        totals[timezone.localtime(session.completed_at).date()] += seconds / 60
    return totals


def study_minutes_by_day(user, start, end):
    totals = defaultdict(float)
    rows = StudySession.objects.filter(user=user, date__range=(start, end)).values('date').annotate(total=Sum('duration_minutes'))
    for row in rows:
        totals[row['date']] += row['total'] or 0
    return totals


def period_totals(user, start, end):
    return {
        'tasks': Task.objects.filter(user=user, status='COMPLETED', completed_at__date__range=(start, end)).count(),
        'focus': int(sum(focus_minutes_by_day(user, start, end).values())),
        'study': int(sum(study_minutes_by_day(user, start, end).values())),
        'habits': HabitLog.objects.filter(habit__user=user, completed=True, date__range=(start, end)).count(),
    }


def activity_buckets(period, start, period_end, focus_by_day, study_by_day):
    """Daily bars for a week, weekly bars for a month."""
    if period == 'monthly':
        ranges, bucket_start = [], start
        while bucket_start <= period_end:
            bucket_end = min(bucket_start + timedelta(days=6), period_end)
            ranges.append((f'{fmt_day(bucket_start)}–{bucket_end.day}', bucket_start, bucket_end))
            bucket_start = bucket_end + timedelta(days=1)
    else:
        ranges = [(f'{start + timedelta(days=i):%a}', start + timedelta(days=i), start + timedelta(days=i)) for i in range(7)]
    labels, focus, study = [], [], []
    for label, first, last in ranges:
        days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
        labels.append(label)
        focus.append(round(sum(focus_by_day.get(day, 0) for day in days)))
        study.append(round(sum(study_by_day.get(day, 0) for day in days)))
    return labels, focus, study


def expected_checkins(habit, first, last):
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    if habit.frequency == 'WEEKLY':
        if habit.target_days:
            return sum(1 for day in days if day.isoweekday() in habit.target_days)
        return len({day.isocalendar()[:2] for day in days})
    return len(days)


def habit_rows(user, start, today):
    habits = list(Habit.objects.filter(user=user, is_active=True))
    logs = defaultdict(set)
    for habit_id, day in HabitLog.objects.filter(
        habit__in=habits, completed=True, date__range=(start, today),
    ).values_list('habit_id', 'date'):
        logs[habit_id].add(day)
    rows = []
    for habit in habits:
        first = max(start, timezone.localtime(habit.created_at).date())
        expected = expected_checkins(habit, first, today) if first <= today else 0
        rows.append({'habit': habit, 'done_days': logs[habit.pk], 'done': len(logs[habit.pk]), 'expected': expected})
    rows.sort(key=lambda row: (-row['done'], -row['habit'].current_streak, row['habit'].name.lower()))
    return rows, len(habits)


# ---------------------------------------------------------------- drawings

def nice_step(peak):
    for step in (15, 30, 60, 120, 180, 240, 360, 480, 600, 720):
        if peak <= step * 4:
            return step
    return math.ceil(peak / 4 / 60) * 60


def activity_chart(labels, focus, study, width):
    height = 44 * mm
    drawing = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x, chart.y = 34, 16
    chart.width, chart.height = width - 40, height - 32
    chart.data = [focus, study]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.style = 'stacked'
    chart.categoryAxis.strokeColor = LINE
    chart.categoryAxis.labels.fontName = 'Helvetica'
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = MUTED
    chart.categoryAxis.labels.dy = -3
    chart.categoryAxis.tickDown = 0
    peak = max([f + s for f, s in zip(focus, study)] + [0])
    step = nice_step(peak)
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = step * max(1, math.ceil(peak / step))
    chart.valueAxis.valueStep = step
    chart.valueAxis.labelTextFormat = lambda value: fmt_minutes(value) if value else '0'
    chart.valueAxis.labels.fontName = 'Helvetica'
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.visibleAxis = False
    chart.valueAxis.tickLeft = 0
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = LINE
    chart.valueAxis.gridStrokeWidth = 0.5
    chart.groupSpacing = 14 if len(labels) <= 7 else 18
    chart.bars.strokeColor = None
    chart.bars[0].fillColor = AMBER
    chart.bars[1].fillColor = BLUE
    drawing.add(chart)

    legend_x = width - 118
    for offset, (name, color) in enumerate((('Focus', AMBER), ('Study', BLUE))):
        x = legend_x + offset * 58
        drawing.add(Rect(x, height - 9, 7, 7, fillColor=color, strokeColor=None, rx=1.5, ry=1.5))
        drawing.add(String(x + 11, height - 8, name, fontName='Helvetica', fontSize=7.5, fillColor=MUTED))
    if not peak:
        drawing.add(String(chart.x + chart.width / 2, chart.y + chart.height / 2, 'No focus or study time logged yet',
                           fontName='Helvetica', fontSize=8, fillColor=FAINT, textAnchor='middle'))
    return drawing


def progress_bar(fraction, width, color=AMBER):
    drawing = Drawing(width, 8)
    drawing.add(Rect(0, 2, width, 4, fillColor=LINE, strokeColor=None, rx=2, ry=2))
    fraction = max(0, min(1, fraction))
    if fraction:
        drawing.add(Rect(0, 2, max(4, width * fraction), 4, fillColor=color, strokeColor=None, rx=2, ry=2))
    return drawing


def week_dots(habit, start, today, done_days):
    drawing = Drawing(7 * 10, 9)
    for index in range(7):
        day = start + timedelta(days=index)
        x = 4 + index * 10
        scheduled = habit.frequency != 'WEEKLY' or not habit.target_days or day.isoweekday() in habit.target_days
        if day in done_days:
            drawing.add(Circle(x, 4.5, 3.4, fillColor=AMBER, strokeColor=None))
        elif day > today or not scheduled:
            drawing.add(Circle(x, 4.5, 1.4, fillColor=LINE, strokeColor=None))
        else:
            drawing.add(Circle(x, 4.5, 3, fillColor=colors.white, strokeColor=FAINT, strokeWidth=0.7))
    return drawing


# ---------------------------------------------------------------- page chrome

class NumberedCanvas(pdf_canvas.Canvas):
    """Draws the footer after layout so it can say 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self.draw_footer(total)
            super().showPage()
        super().save()

    def draw_footer(self, total):
        width = A4[0]
        self.saveState()
        self.setStrokeColor(LINE)
        self.setLineWidth(0.6)
        self.line(18 * mm, 13 * mm, width - 18 * mm, 13 * mm)
        self.setFillColor(FAINT)
        self.setFont('Helvetica', 7.5)
        self.drawString(18 * mm, 8.5 * mm, 'FocusForge  ·  Build better days, one session at a time.')
        self.drawRightString(width - 18 * mm, 8.5 * mm, f'Page {self._pageNumber} of {total}')
        self.restoreState()


# ---------------------------------------------------------------- sections

def header_block(display_name, period, label, generated_at, width):
    left = [Paragraph(f'{"MONTHLY" if period == "monthly" else "WEEKLY"} PRODUCTIVITY REPORT', STYLES['eyebrow']),
            Paragraph('FocusForge', STYLES['brand'])]
    right = [Paragraph(escape(display_name), STYLES['header_name']),
             Paragraph(escape(label), STYLES['header_right']),
             Paragraph(f'Generated {fmt_day(generated_at)}, {generated_at.year} at {dateformat.format(generated_at, "g:i A")}',
                       STYLES['header_right'])]
    table = Table([[left, right]], colWidths=[width * 0.5, width * 0.5])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 16), ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 14), ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LINEBELOW', (0, 0), (-1, -1), 2.5, AMBER),
    ]))
    return table


def card(label, value, note, note_color, zero=False):
    note_style = ParagraphStyle('note', parent=STYLES['card_note'], textColor=note_color)
    return [Paragraph(label.upper(), STYLES['card_label']),
            Paragraph(escape(value), STYLES['card_value_muted' if zero else 'card_value']),
            Paragraph(escape(note), note_style)]


def kpi_row(cards, width):
    gap = 3 * mm
    card_width = (width - gap * (len(cards) - 1)) / len(cards)
    row, widths, commands = [], [], [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 9), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    for index, (content, highlight) in enumerate(cards):
        if index:
            row.append('')
            widths.append(gap)
        column = len(row)
        row.append(content)
        widths.append(card_width)
        commands += [('BACKGROUND', (column, 0), (column, 0), AMBER_SOFT if highlight else SOFT),
                     ('BOX', (column, 0), (column, 0), 0.6, AMBER if highlight else LINE)]
    table = Table([row], colWidths=widths)
    table.setStyle(TableStyle(commands))
    return table


def habits_block(rows, total_habits, period, start, today, width):
    if not rows:
        return [Paragraph('No active habits yet. Add one to start building a streak.', STYLES['empty'])]
    data = []
    for row in rows[:MAX_HABITS]:
        habit = row['habit']
        streak = f'<br/><font size="7" color="#6b7280">{habit.current_streak}-day streak</font>' if habit.current_streak >= 2 else ''
        name = Paragraph(escape(habit.name[:60]) + streak, STYLES['cell'])
        if period == 'weekly':
            visual = week_dots(habit, start, today, row['done_days'])
        else:
            visual = progress_bar(row['done'] / row['expected'] if row['expected'] else 0, 26 * mm)
        count = f"{row['done']}/{row['expected']}" if row['expected'] else str(row['done'])
        data.append([name, visual, Paragraph(count, ParagraphStyle('count', parent=STYLES['cell'], alignment=TA_RIGHT))])
    table = Table(data, colWidths=[width - 46 * mm, 32 * mm, 14 * mm])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LINE),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    flowables = [table]
    if total_habits > MAX_HABITS:
        flowables.append(Paragraph(f'+ {plural(total_habits - MAX_HABITS, "more habit")}', STYLES['small']))
    return flowables


def goals_block(user, today, width):
    goals = list(Goal.objects.filter(user=user, status='ACTIVE').annotate(
        milestone_total=Count('milestones'),
        milestone_done=Count('milestones', filter=Q(milestones__is_completed=True)),
    ).order_by('deadline')[:MAX_GOALS + 1])
    if not goals:
        return [Paragraph('No active goals. Set one with a few milestones to track it here.', STYLES['empty'])]
    data = []
    for goal in goals[:MAX_GOALS]:
        if goal.deadline < today:
            due = f'<font color="#dc2626">overdue since {fmt_day(goal.deadline)}</font>'
        else:
            due = f'due {fmt_day(goal.deadline)}'
        meta = f'{goal.milestone_done}/{goal.milestone_total} milestones · {due}'
        title = Paragraph(f'{escape(goal.title[:70])}<br/><font size="7" color="#6b7280">{meta}</font>', STYLES['cell'])
        percent = goal.completion_percentage or 0
        data.append([title, progress_bar(percent / 100, 22 * mm),
                     Paragraph(f'{percent}%', ParagraphStyle('pct', parent=STYLES['cell'], alignment=TA_RIGHT))])
    table = Table(data, colWidths=[width - 36 * mm, 24 * mm, 12 * mm])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, LINE),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    flowables = [table]
    if len(goals) > MAX_GOALS:
        flowables.append(Paragraph('+ more active goals in the app', STYLES['small']))
    return flowables


def highlights(user, start, today, focus_by_day, study_by_day, completed_tasks, habit_rows_data):
    items = []
    day_totals = {day: focus_by_day.get(day, 0) + study_by_day.get(day, 0) for day in set(focus_by_day) | set(study_by_day)}
    if day_totals:
        best_day, minutes = max(day_totals.items(), key=lambda item: item[1])
        if minutes:
            items.append(f'<b>Best day:</b> {best_day:%A}, {fmt_day(best_day)} with {fmt_minutes(minutes)} of focus and study.')
    categories = Counter(name for name in completed_tasks.values_list('category__name', flat=True) if name)
    if categories:
        name, count = categories.most_common(1)[0]
        items.append(f'<b>Most completed category:</b> {escape(name)} ({plural(count, "task")}).')
    streaks = [row['habit'] for row in habit_rows_data if row['habit'].current_streak >= 2]
    if streaks:
        top = max(streaks, key=lambda habit: habit.current_streak)
        items.append(f'<b>Longest streak:</b> {escape(top.name[:60])} is on a {top.current_streak}-day streak. Keep it going.')
    milestones = Milestone.objects.filter(goal__user=user, is_completed=True, completed_at__date__range=(start, today)).count()
    if milestones:
        items.append(f'<b>Goal progress:</b> {plural(milestones, "milestone")} completed.')
    overdue = Task.objects.filter(user=user, status__in=['PENDING', 'IN_PROGRESS'], due_date__lt=timezone.now()).count()
    if overdue:
        items.append(f'<b>Needs attention:</b> {plural(overdue, "task")} overdue. Plan {"it" if overdue == 1 else "them"} first.')
    if not items:
        items.append('No activity recorded yet this period. One small task or a 25-minute focus session is a great start.')
    return [Paragraph(item, STYLES['bullet'], bulletText='•') for item in items]


def tasks_block(completed_tasks, total, width):
    if not total:
        return [Paragraph('No completed tasks in this period yet.', STYLES['empty'])]
    head = [Paragraph(text, STYLES['cell_head']) for text in ('TASK', 'CATEGORY', 'PRIORITY', 'COMPLETED')]
    rows = [head]
    for task in completed_tasks[:MAX_TASK_ROWS]:
        priority_style = ParagraphStyle('priority', parent=STYLES['cell'], textColor=PRIORITY_COLORS.get(task.priority, TEXT))
        rows.append([
            Paragraph(escape(task.title), STYLES['cell']),
            Paragraph(escape(task.category.name) if task.category else '—', STYLES['cell']),
            Paragraph(task.get_priority_display(), priority_style),
            Paragraph(fmt_day(timezone.localtime(task.completed_at).date()), STYLES['cell']),
        ])
    commands = [
        ('BACKGROUND', (0, 0), (-1, 0), SOFT),
        ('LINEBELOW', (0, 0), (-1, 0), 0.8, LINE),
        ('LINEBELOW', (0, 1), (-1, -2), 0.4, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
    ]
    if total > MAX_TASK_ROWS:
        # Kept inside the table so it never ends up alone on a new page.
        rows.append([Paragraph(f'… and {plural(total - MAX_TASK_ROWS, "more completed task")}', STYLES['small']), '', '', ''])
        commands.append(('SPAN', (0, -1), (-1, -1)))
    table = Table(rows, colWidths=[width - 82 * mm, 32 * mm, 24 * mm, 26 * mm], repeatRows=1)
    table.setStyle(TableStyle(commands))
    return [table]


def two_columns(left, right, width):
    gap = 8 * mm
    column = (width - gap) / 2
    table = Table([[left, '', right]], colWidths=[column, gap, column])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return table


# ---------------------------------------------------------------- entry point

def build_productivity_report(user, period='weekly', today=None):
    """Return the report as PDF bytes."""
    from .views import weekly_consistency_score

    period = period if period in ('weekly', 'monthly') else 'weekly'
    today = today or timezone.localdate()
    start, period_end, previous_start, previous_end, label, compare_label = period_bounds(period, today)

    current = period_totals(user, start, today)
    previous = period_totals(user, previous_start, previous_end)
    focus_by_day = focus_minutes_by_day(user, start, today)
    study_by_day = study_minutes_by_day(user, start, today)
    completed_tasks = Task.objects.filter(
        user=user, status='COMPLETED', completed_at__date__range=(start, today),
    ).select_related('category').order_by('-completed_at')
    habit_rows_data, total_habits = habit_rows(user, start, today)

    buffer = BytesIO()
    display_name = user.get_full_name() or user.username
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=20 * mm,
        title=f'FocusForge {period} report', author=display_name,
    )
    # The frame adds 6pt padding on each side; tables must fit inside it to line up with headings.
    width = document.width - 12

    cards = []
    for key, name, minutes in (('tasks', 'Tasks done', False), ('focus', 'Focus time', True),
                               ('study', 'Study time', True), ('habits', 'Habit check-ins', False)):
        value = fmt_minutes(current[key]) if minutes else str(current[key])
        note, color = delta_note(current[key], previous[key], compare_label, minutes)
        cards.append((card(name, value, note, color, zero=not current[key]), False))
    if period == 'weekly':
        score = weekly_consistency_score(user, today)
        cards.append((card('Consistency', f'{score}%', 'tasks + habits on track', MUTED), True))
    else:
        active_days = {timezone.localtime(task.completed_at).date() for task in completed_tasks}
        active_days |= set(HabitLog.objects.filter(habit__user=user, completed=True, date__range=(start, today)).values_list('date', flat=True))
        active_days |= {day for day, minutes in focus_by_day.items() if minutes} | {day for day, minutes in study_by_day.items() if minutes}
        elapsed = (today - start).days + 1
        cards.append((card('Active days', f'{len(active_days)}/{elapsed}', 'days with any activity', MUTED), True))

    labels, focus_series, study_series = activity_buckets(period, start, period_end, focus_by_day, study_by_day)
    column_width = (width - 8 * mm) / 2
    total_completed = completed_tasks.count()

    story = [
        header_block(display_name, period, label, timezone.localtime(), width),
        Spacer(1, 6 * mm),
        kpi_row(cards, width),
        KeepTogether([
            Paragraph('Daily activity' if period == 'weekly' else 'Weekly activity', STYLES['section']),
            activity_chart(labels, focus_series, study_series, width),
        ]),
        KeepTogether([two_columns(
            [Paragraph('Habits', STYLES['section'])] + habits_block(habit_rows_data, total_habits, period, start, today, column_width),
            [Paragraph('Goals', STYLES['section'])] + goals_block(user, today, column_width),
            width,
        )]),
        KeepTogether([Paragraph('Highlights', STYLES['section'])]
                     + highlights(user, start, today, focus_by_day, study_by_day, completed_tasks, habit_rows_data)),
        Paragraph(f'Completed tasks ({total_completed})', STYLES['section']),
        *tasks_block(completed_tasks, total_completed, width),
    ]
    document.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
