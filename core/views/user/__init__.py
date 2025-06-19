# __init__.py для user views
from .register import RegisterView
from .token import CustomTokenObtainPairView
from .history import HistoryListCreateView
from .shikimori import ShikimoriProxyView
from .profile import UserProfileView
from .avatar import UserAvatarUpdateView
from .bookmark import BookmarkUpdateView
from .bookmark_history import BookmarkHistoryView
from .email_code import SendEmailCodeView
from .register_with_code import RegisterWithCodeView
from .public_info import PublicUserInfoView
