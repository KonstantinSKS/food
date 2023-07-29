from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    SignupSerializer, UserSerializer, TagSerializer,
    IngredientSerializer, IngredientsCreateOrUpdateSerializer,
    IngredientsReadOnlySerializer,
    RecipeCreateOrUpdateSerializer, RecipeReadOnlySerializer,
    FavoriteRecipeSerializer, SubscriptionSerializer)
from .pagination import LimitPagesPagination
from .permissions import IsAdminOrReadOnly, IsAdminOrAuthorOrReadOnly
from .filters import IngredientFilter, RecipeFilter
from users.models import User, Subscription
from recipes.models import (Tag, Ingredient, Recipe,
                            AmountOfIngredients, Favorite, ShoppingList)

# from rest_framework.permissions import AllowAny # Временно!


class UserViewSet(viewsets.ModelViewSet):
    ...


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = TagSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('id')
    permission_classes = (IsAdminOrAuthorOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = LimitPagesPagination

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadOnlySerializer
        return RecipeCreateOrUpdateSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = self.request.user

        if self.request.method == 'POST':
            if Favorite.objects.filter(
                user=user,
                recipe=recipe
            ).exists():
                raise exceptions.ValidationError('Рецепт уже в избранном.')

            Favorite.objects.create(user=user, recipe=recipe)
            serializer = FavoriteRecipeSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self.request.method == 'DELETE':
            get_object_or_404(Favorite, user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=(IsAuthenticated,))
    def shopping_list(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = self.request.user

        if self.request.method == 'POST':
            if ShoppingList.objects.filter(
                user=user,
                recipe=recipe
            ).exists():
                raise exceptions.ValidationError('Рецепт уже в избранном.')

            ShoppingList.objects.create(user=user, recipe=recipe)
            serializer = FavoriteRecipeSerializer(
                recipe,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if self.request.method == 'DELETE':
            get_object_or_404(ShoppingList, user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            permission_classes=(IsAuthenticated,))
    def download_shopping_cart(self, request):
        user = self.request.user
        ingredients = (AmountOfIngredients.objects.filter(
            recipe__shoppinglist__user=request.user) #!!!!!!!
            .values('ingredient__name', 'ingredient__measurement_unit') #!!!!!
            .annotate(amount=Sum('amount'))
        )
        count = 1
        text = 'Список покупок:\n'
        filename = f'{user.username}_shopping_list.txt'
        for item in ingredients:
            name, measurement_unit, amount = list(item.values())
            text += f'{count}. {name} ({measurement_unit}) — {amount}\n'
            count += 1
        response = HttpResponse(text, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response


class AmountOfIngredientsViewSet(viewsets.ModelViewSet):
    ...


class ShoppingListViewSet(viewsets.ModelViewSet):
    ...


class FavoriteViewSetviewsets(viewsets.ModelViewSet):
    ...
