from PyQt6.QtWidgets import QStackedWidget, QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup


class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_speed = 250
        self.m_active = False

    def setCurrentIndex(self, index):
        if self.currentIndex() == index:
            return
        if self.m_active:
            return

        self.m_active = True
        
        current_widget = self.currentWidget()
        next_widget = self.widget(index)
        
        if not current_widget:
            super().setCurrentIndex(index)
            self.m_active = False
            return
            
        # Apply opacity effects
        self.current_effect = QGraphicsOpacityEffect(current_widget)
        current_widget.setGraphicsEffect(self.current_effect)
        
        self.next_effect = QGraphicsOpacityEffect(next_widget)
        self.next_effect.setOpacity(0.0)
        next_widget.setGraphicsEffect(self.next_effect)
        
        next_widget.show()
        next_widget.raise_()

        self.anim_group = QParallelAnimationGroup()
        
        anim_out = QPropertyAnimation(self.current_effect, b"opacity")
        anim_out.setDuration(self.m_speed)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        anim_out.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        anim_in = QPropertyAnimation(self.next_effect, b"opacity")
        anim_in.setDuration(self.m_speed)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim_group.addAnimation(anim_out)
        self.anim_group.addAnimation(anim_in)
        
        self.next_index = index
        self.anim_group.finished.connect(self.animation_done)
        self.anim_group.start()

    def animation_done(self):
        super().setCurrentIndex(self.next_index)
        
        for i in range(self.count()):
            w = self.widget(i)
            w.setGraphicsEffect(None)

        self.m_active = False
