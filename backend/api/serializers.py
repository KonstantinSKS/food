from rest_framework import serializers, validators
from django.core.validators import MinValueValidator
# from django.shortcuts import get_object_or_404

from drf_extra_fields.fields import Base64ImageField

from recipes.models import (Tag, Ingredient, Recipe,
                            AmountOfIngredients)
from users.models import User, Subscription


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, max_length=254)
    username = serializers.RegexField(
        regex=r'^[\w.@+-]',
        max_length=150,
        required=True,
    )

    class Meta:
        model = User

    def validate(self, data):
        email = data.get('email')
        username = data.get('username')
        user_email_exists = User.objects.filter(email=email).exists()
        user_username_exists = User.objects.filter(username=username).exists()
        if (user_email_exists
                and not user_username_exists):
            raise serializers.ValidationError(
                'User with such email already exists')
        if (not user_email_exists
                and user_username_exists):
            raise serializers.ValidationError(
                'User with such username already exists')
        return data


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)
# default=False

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Subscription.objects.filter(user=self.context['request'].user,
                                            author=obj).exists())


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientsCreateOrUpdateSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(
        validators=(MinValueValidator(1),)
    )

    class Meta:
        model = AmountOfIngredients
        fields = (
            'id',
            'amount',
        )


class IngredientsReadOnlySerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = AmountOfIngredients
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class RecipeCreateOrUpdateSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = IngredientsCreateOrUpdateSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(),
                                              many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        validators=(MinValueValidator(1),)
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )
        validators = [
            validators.UniqueTogetherValidator(
                queryset=AmountOfIngredients.objects.all(),
                fields=('recipe', 'ingredient')
            )
        ]

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Рецепт должен содержать минимум 1 ингредиент!'
            )
        for ingredient in ingredients:
            if int(ingredient.get('amount')) < 1:
                raise serializers.ValidationError(
                    'Количество не может быть меньше 1 единицы!'
                )
        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError(
                'Для рецепта нужен хотя бы один тег!'
            )
        return tags

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) < 1:
            raise serializers.ValidationError(
                'Время приготовления меньше 1 минуты!'
            )
        return cooking_time

    def create_AmountOfIngredients(self, ingredients, recipe):
        for ingredient in ingredients:
            ingredient = ingredient.get('id')
            amount = ingredient.get('amount')
            AmountOfIngredients.objects.create(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount,
            )

    def create(self, validated_data):
        #  author =
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_AmountOfIngredients(
            recipe=recipe, ingredients=ingredients)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)

        if 'tags' in validated_data:
            tags = validated_data.pop('tags')
            instance.tags.clear()
            instance.tags.set(tags)

        return super().update(
            instance, validated_data)
        # instance.save()
        # return instance

    # def to_representation(self, instance):


class RecipeReadOnlySerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientsReadOnlySerializer(many=True)
    is_favorited = serializers.SerializerMethodField()
    # serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField()
    # serializers.BooleanField(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_is_favorited(self, recipe):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return user.favorites.filter(recipe=recipe).exists()

    def get_is_in_shopping_cart(self, recipe):
        user = self.context.get('request').user
        if not user.is_anonymous:
            return user.shoppinglist.filter(recipe=recipe).exists()


class FavoriteRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class SubscriptionSerializer(UserSerializer):
    recipes = FavoriteRecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()
# Не понятно, будет ли работать этот сериализатор ?

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )

    def get_is_subscribed(self, obj):
        return (
            self.context.get('request').user.is_authenticated
            and Subscription.objects.filter(user=self.context['request'].user,
                                            author=obj).exists()

        )

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def validate(self, data):
        if self.context['request'].method == 'POST':
            user = self.context.get('user')
            author = self.context.get('author')  # author = self.instance
            if User.objects.filter(
                    user=user, author=author).exists():
                raise serializers.ValidationError(
                    'Вы уже подписаны на этого пользователя!')
            if user == author:
                raise serializers.ValidationError(
                    'Нельзя подписаться на самого себя!')
        return data
