from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import permissions, routers, serializers, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from .models import ChatMessage, ChatSession
from .services import ChatConversationManager


class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ["id", "created_at"]


class ChatMessageCreateSerializer(serializers.Serializer):
    """Validate request body with this serializer."""

    content = serializers.CharField()
    session_id = serializers.IntegerField(required=False)


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["sender", "content", "timestamp"]


class ChatAPIViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        user = self.request.user

        if not user.is_authenticated:
            return ChatSession.objects.none()

        return ChatSession.objects.filter(user=user).order_by("-created_at")

    def list(self, request: Request) -> Response:
        queryset = self.get_queryset()
        serializer = ChatSessionSerializer(queryset, many=True)

        return Response(data=serializer.data)

    def create(self, request: Request) -> Response:
        serializer = ChatMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_message = serializer.validated_data["content"]
        session_id = serializer.validated_data.get("session_id")

        manager = ChatConversationManager(user=request.user)
        manager.get_or_create_session(session_id=session_id)

        response = manager.process_message(user_message=user_message)

        return Response(data=response, status=status.HTTP_201_CREATED)

    def retrieve(self, request: Request, pk=None) -> Response:
        """Retrieve all messages for a specific chat session."""

        session = get_object_or_404(ChatSession, pk=pk)
        messages = session.messages.all()
        serializer = ChatMessageSerializer(messages, many=True)

        return Response(serializer.data)


router = routers.DefaultRouter()
router.register(prefix="", viewset=ChatAPIViewSet, basename="chat")
