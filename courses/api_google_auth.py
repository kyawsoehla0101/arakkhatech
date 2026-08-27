import json
import time
import base64
import hashlib
from typing import Optional, Dict, Any
from urllib.request import urlopen, Request
from urllib.parse import urlencode

from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.db.models import Q

from .models import Profile
from .serializers import UserSerializer


GOOGLE_TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo'
GOOGLE_CERTS_URL = 'https://www.googleapis.com/oauth2/v3/certs'


def _b64url_decode(data: str) -> bytes:
    remainder = len(data) % 4
    if remainder:
        data += '=' * (4 - remainder)
    return base64.urlsafe_b64decode(data.encode('utf-8'))


def _fetch_google_certs() -> Dict[str, Any]:
    try:
        req = Request(GOOGLE_CERTS_URL, headers={'User-Agent': 'ArakkhaTech/1.0'})
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return {}


_CACHED_CERTS = {'data': {}, 'exp': 0}


def _get_google_cert(kid: str) -> Optional[Dict[str, Any]]:
    now = int(time.time())
    if _CACHED_CERTS['exp'] < now or not _CACHED_CERTS.get('data'):
        certs = _fetch_google_certs()
        _CACHED_CERTS['data'] = {c.get('kid'): c for c in certs.get('keys', []) if c.get('kid')}
        _CACHED_CERTS['exp'] = now + 60 * 60 * 3
    return _CACHED_CERTS['data'].get(kid)


def _rsa_verify(message: bytes, signature: bytes, n: int, e: int) -> bool:
    try:
        s = int.from_bytes(signature, byteorder='big')
        m = pow(s, e, n)
        encoded = m.to_bytes((n.bit_length() + 7) // 8, byteorder='big')
        if not encoded or encoded[0] != 0:
            return False
        expected_digest = hashlib.sha256(message).digest()
        if b'\x00\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20' + expected_digest in encoded:
            return True
        return False
    except Exception:
        return False


def verify_google_id_token_locally(id_token: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    try:
        parts = id_token.split('.')
        if len(parts) != 3:
            return None
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
        signing_input = (parts[0] + '.' + parts[1]).encode('utf-8')
        signature = _b64url_decode(parts[2])
        alg = header.get('alg')
        if alg not in ('RS256',):
            return None
        kid = header.get('kid')
        cert = _get_google_cert(kid) if kid else None
        if cert:
            n_int = int.from_bytes(_b64url_decode(cert['n']), 'big')
            e_int = int.from_bytes(_b64url_decode(cert['e']), 'big')
            if not _rsa_verify(signing_input, signature, n_int, e_int):
                return None
        else:
            return None
        now = int(time.time())
        if int(payload.get('exp', 0)) < now - 60:
            return None
        if int(payload.get('iat', now + 3600)) > now + 300:
            return None
        if payload.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
            return None
        if payload.get('aud'):
            auds = payload['aud'] if isinstance(payload['aud'], list) else [payload['aud']]
            if client_id and client_id not in auds:
                return None
        if not payload.get('email_verified'):
            return None
        return payload
    except Exception:
        return None


def verify_google_token_online(token: str, client_id: Optional[str] = None, is_access: bool = False) -> Optional[Dict[str, Any]]:
    try:
        params = {'access_token' if is_access else 'id_token': token}
        url = GOOGLE_TOKENINFO_URL + '?' + urlencode(params)
        req = Request(url, headers={'User-Agent': 'ArakkhaTech/1.0'})
        with urlopen(req, timeout=10) as resp:
            info = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None
    if client_id and str(info.get('aud') or info.get('issued_to') or '') != client_id:
        return None
    if is_access and not info.get('email'):
        return None
    if not is_access and not info.get('email_verified'):
        return None
    return info


def get_google_identity(id_token: Optional[str] = None, access_token: Optional[str] = None,
                        client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if id_token:
        payload = verify_google_id_token_locally(id_token, client_id=client_id)
        if payload and payload.get('email'):
            return payload
        payload = verify_google_token_online(id_token, client_id=client_id, is_access=False)
        if payload and payload.get('email'):
            return payload
    if access_token:
        payload = verify_google_token_online(access_token, client_id=client_id, is_access=True)
        if payload and payload.get('email'):
            return payload
    return None


def create_or_get_google_user(info: Dict[str, Any]) -> User:
    email = str(info.get('email', '')).strip().lower()
    first_name = str(info.get('given_name') or info.get('first_name') or '').strip()
    last_name = str(info.get('family_name') or info.get('last_name') or '').strip()
    name = str(info.get('name') or '').strip()
    if not first_name and not last_name and name:
        spl = name.split(' ', 1)
        first_name = spl[0]
        last_name = spl[1] if len(spl) > 1 else ''

    user = User.objects.filter(email__iexact=email).first()
    if user:
        changed = False
        if not user.first_name and first_name:
            user.first_name = first_name
            changed = True
        if not user.last_name and last_name:
            user.last_name = last_name
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if changed:
            user.save()
    else:
        base_username = (email.split('@')[0]).lower()
        if not base_username:
            base_username = 'googleuser'
        candidate = base_username
        suffix = 1
        while User.objects.filter(username__iexact=candidate).exists():
            candidate = f"{base_username}{suffix}"
            suffix += 1
        user = User.objects.create(
            username=candidate,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        user.set_unusable_password()
        user.save()

    profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
    if not profile.role:
        profile.role = 'student'
        profile.save(update_fields=['role'])
    return user


def generate_tokens_for(user: User) -> Dict[str, Any]:
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True,
                                     help_text="Flutter/Firebase GoogleSignIn မှ ရရှိသော idToken")
    access_token = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True,
                                         help_text="OAuth access token (id_token မပါသောအခါသုံး)")

    def validate(self, attrs):
        if not attrs.get('id_token') and not attrs.get('access_token'):
            raise serializers.ValidationError("id_token သို့မဟုတ် access_token တစ်ခုအနည်းဆုံး ထည့်ပေးပါ")
        return attrs


class GoogleAuthAPIView(APIView):
    """
    Flutter GoogleSignIn မှ ရရှိသော id_token (သို့) access_token ကို server side မှာ verify လုပ်ပြီး
    User + Profile(student) အသစ်ဖန်တီး သို့မဟုတ် ရှိပြီးသား user ကို ယူပြီး JWT access+refresh tokens ပြန်ပေးသည်။
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from decouple import config as _config
        client_id = _config('GOOGLE_CLIENT_ID', default=None) or None

        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        info = get_google_identity(
            id_token=data.get('id_token') or None,
            access_token=data.get('access_token') or None,
            client_id=client_id,
        )
        if not info or not info.get('email'):
            return Response({
                'status': 'error',
                'message': 'Google token မှားယွင်းနေပါသည်။ ပြန်လည်စမ်းသပ်ပေးပါ။'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = create_or_get_google_user(info)
        except Exception:
            return Response({
                'status': 'error',
                'message': 'User အကောင့် တည်ဆောက်ရာတွင် အမှားအယွင်းရှိနေပါသည်။'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        tokens = generate_tokens_for(user)
        return Response({
            'status': 'success',
            'message': 'Google ဖြင့် login ဝင်ခြင်း အောင်မြင်ပါသည်',
            'tokens': tokens,
            'user': UserSerializer(user, context={'request': request}).data,
        }, status=status.HTTP_200_OK)


class CurrentUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({
            'status': 'success',
            'user': UserSerializer(request.user, context={'request': request}).data,
        })
