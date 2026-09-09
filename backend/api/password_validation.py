from django.core.exceptions import ValidationError

class SimpleComplexityPasswordValidator:
    """
    Validador de complexidade simples de senha para a Forja:
    - 8 ou mais caracteres;
    - Pelo menos uma letra (isalpha);
    - Pelo menos um dígito (isdigit);
    - Pelo menos um caractere especial (não alfanumérico e não espaço).
    """

    def validate(self, password, user=None):
        if len(password) < 8:
            raise ValidationError(
                "A senha deve conter no mínimo 8 caracteres.",
                code='password_too_short'
            )

        has_letter = any(c.isalpha() for c in password)
        if not has_letter:
            raise ValidationError(
                "A senha deve conter pelo menos uma letra.",
                code='password_no_letter'
            )

        has_digit = any(c.isdigit() for c in password)
        if not has_digit:
            raise ValidationError(
                "A senha deve conter pelo menos um dígito.",
                code='password_no_digit'
            )

        has_special = any(not c.isalnum() and not c.isspace() for c in password)
        if not has_special:
            raise ValidationError(
                "A senha deve conter pelo menos um caractere especial (espaço não conta).",
                code='password_no_special'
            )

    def get_help_text(self):
        return "Sua senha deve ter no mínimo 8 caracteres, com pelo menos uma letra, um número e um caractere especial."
