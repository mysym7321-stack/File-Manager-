import os
import shutil
from pathlib import Path
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.utils import platform

# ============ إعدادات ============
WHATSAPP_NUMBER = "967714481063"  # رقمك بصيغة دولية
WHATSAPP_MESSAGE = "مرحباً، تواصلت معك من تطبيق مدير الملفات"


# ============ إدارة التخزين ============
class StorageManager:
    def __init__(self):
        if platform == 'android':
            from android.storage import app_storage_path
            self.private_root = Path(app_storage_path())
        else:
            self.private_root = Path.home() / '.filemanager'

        self.private_root.mkdir(parents=True, exist_ok=True)

        # الخزنة المخفية: مجلد يبدأ بنقطة + .nomedia
        self.vault_dir = self.private_root / '.vault'
        self.vault_dir.mkdir(exist_ok=True)
        (self.vault_dir / '.nomedia').touch()

    def list_files(self, path):
        p = Path(path)
        if not p.exists():
            return []
        items = []
        for item in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if item.name.startswith('.'):
                continue
            items.append({
                'name': item.name,
                'path': str(item),
                'is_dir': item.is_dir()
            })
        return items

    def import_to_vault(self, src_path):
        src = Path(src_path)
        if not src.exists():
            return False, "الملف غير موجود"
        dst = self.vault_dir / src.name
        counter = 1
        while dst.exists():
            dst = self.vault_dir / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        shutil.move(str(src), str(dst))
        return True, f"تم النقل: {dst.name}"

    def list_vault(self):
        return [f for f in self.vault_dir.iterdir() if f.name != '.nomedia']

    def restore_from_vault(self, filepath):
        src = Path(filepath)
        dst = self.private_root / src.name
        counter = 1
        while dst.exists():
            dst = self.private_root / f"{src.stem}_{counter}{src.suffix}"
            counter += 1
        shutil.move(str(src), str(dst))
        return True, f"تمت الاستعادة: {dst.name}"


# ============ الواجهة الرئيسية ============
class FileManagerUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.storage = StorageManager()
        self.current_path = self.storage.private_root

        # شريط العنوان
        self.title = Label(
            text=f"📁 {self.current_path.name or 'الجذر'}",
            size_hint_y=0.08,
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.add_widget(self.title)

        # قائمة الملفات
        self.scroll = ScrollView()
        self.file_list = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.file_list.bind(minimum_height=self.file_list.setter('height'))
        self.scroll.add_widget(self.file_list)
        self.add_widget(self.scroll)

        # الشريط السفلي: رجوع / الخزنة / تحديث / واتساب
        btn_bar = BoxLayout(size_hint_y=0.12, spacing=5, padding=5)

        btn_back = Button(text="↩ رجوع", on_release=self.go_back)
        btn_vault = Button(text="🔒 الخزنة", on_release=self.show_vault)
        btn_refresh = Button(text="🔄 تحديث", on_release=lambda x: self.refresh())
        btn_whatsapp = Button(
            text="💬 تواصل معنا",
            background_color=(0.15, 0.7, 0.3, 1)
        )
        btn_whatsapp.bind(on_release=self.open_whatsapp)

        btn_bar.add_widget(btn_back)
        btn_bar.add_widget(btn_vault)
        btn_bar.add_widget(btn_refresh)
        btn_bar.add_widget(btn_whatsapp)
        self.add_widget(btn_bar)

        self.refresh()

    # ---------- عرض الملفات ----------
    def refresh(self):
        self.file_list.clear_widgets()
        try:
            items = self.storage.list_files(self.current_path)
        except PermissionError:
            items = []
            self.title.text = "⚠ لا يوجد إذن للوصول"

        if not items:
            self.file_list.add_widget(Label(
                text="(فارغ أو لا يوجد إذن)",
                size_hint_y=None, height=50
            ))

        for item in items:
            btn = Button(
                text=f"{'📁' if item['is_dir'] else '📄'} {item['name']}",
                size_hint_y=None, height=55,
                halign='left'
            )
            btn.bind(
                on_release=lambda x, p=item['path'], d=item['is_dir']:
                self.on_item_click(p, d)
            )
            self.file_list.add_widget(btn)

    def on_item_click(self, path, is_dir):
        if is_dir:
            self.current_path = Path(path)
            self.title.text = f"📁 {self.current_path.name}"
            self.refresh()
        else:
            self.show_file_options(path)

    def show_file_options(self, filepath):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f"الملف:\n{Path(filepath).name}"))

        btn_vault = Button(text="🔒 نقل إلى الخزنة المخفية",
                           size_hint_y=None, height=50)
        btn_vault.bind(on_release=lambda x: self.do_import_vault(filepath))

        btn_cancel = Button(text="إلغاء", size_hint_y=None, height=50)

        popup = Popup(title="خيارات الملف", content=content,
                      size_hint=(0.9, 0.5))
        btn_cancel.bind(on_release=popup.dismiss)

        content.add_widget(btn_vault)
        content.add_widget(btn_cancel)
        popup.open()

    def do_import_vault(self, filepath):
        ok, msg = self.storage.import_to_vault(filepath)
        self.show_toast("✅ تم" if ok else "❌ خطأ", msg)
        self.refresh()

    # ---------- الخزنة ----------
    def show_vault(self):
        vault_files = self.storage.list_vault()
        content = BoxLayout(orientation='vertical', spacing=5, padding=10)

        scroll = ScrollView(size_hint_y=0.8)
        inner = GridLayout(cols=1, size_hint_y=None, spacing=2)
        inner.bind(minimum_height=inner.setter('height'))

        if not vault_files:
            inner.add_widget(Label(text="الخزنة فارغة",
                                   size_hint_y=None, height=50))

        for f in vault_files:
            btn = Button(text=f"📄 {f.name}", size_hint_y=None, height=50)
            btn.bind(on_release=lambda x, p=str(f):
                     self.restore_from_vault(p))
            inner.add_widget(btn)

        scroll.add_widget(inner)
        content.add_widget(Label(text="🔒 الخزنة المخفية", size_hint_y=0.1))
        content.add_widget(scroll)

        btn_close = Button(text="إغلاق", size_hint_y=0.1)
        popup = Popup(title="الخزنة", content=content, size_hint=(0.9, 0.8))
        btn_close.bind(on_release=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

    def restore_from_vault(self, filepath):
        ok, msg = self.storage.restore_from_vault(filepath)
        self.show_toast("✅ تم" if ok else "❌ خطأ", msg)
        self.refresh()

    # ---------- واتساب ----------
    def open_whatsapp(self):
        if platform != 'android':
            self.show_toast("تنبيه", "واتساب متاح فقط على Android")
            return
        try:
            from jnius import autoclass
            from android import mActivity

            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')

            url = f"https://wa.me/{WHATSAPP_NUMBER}?text={Uri.encode(WHATSAPP_MESSAGE)}"

            # 1) واتساب العادي
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(url))
            intent.setPackage("com.whatsapp")
            try:
                mActivity.startActivity(intent)
                return
            except Exception:
                pass

            # 2) واتساب بزنس
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(url))
            intent.setPackage("com.whatsapp.w4b")
            try:
                mActivity.startActivity(intent)
                return
            except Exception:
                pass

            # 3) المتصفح كخطة أخيرة
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(url))
            mActivity.startActivity(intent)

        except Exception as e:
            self.show_toast("خطأ", f"تعذر فتح واتساب: {e}")

    # ---------- أدوات ----------
    def show_toast(self, title, msg):
        popup = Popup(title=title, content=Label(text=msg),
                      size_hint=(0.8, 0.3))
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2)

    def go_back(self):
        parent = self.current_path.parent
        if parent.exists() and str(parent).startswith(
                str(self.storage.private_root.parent)):
            self.current_path = parent
            self.title.text = f"📁 {parent.name or 'الجذر'}"
            self.refresh()


# ============ نقطة الدخول ============
class FileManagerApp(App):
    def build(self):
        self.title = "مدير الملفات"
        return FileManagerUI()


if __name__ == '__main__':
    FileManagerApp().run()
