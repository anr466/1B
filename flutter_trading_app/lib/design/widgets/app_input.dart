import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

/// App Input — حقل إدخال موحد مع validation + RTL
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class AppInput extends StatelessWidget {
  final TextEditingController? controller;
  final String? label;
  final String? hint;
  final String? errorText;
  final bool obscureText;
  final bool readOnly;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final int? maxLines;
  final int? maxLength;
  final Widget? prefixIcon;
  final Widget? suffixIcon;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final FormFieldValidator<String>? validator;
  final FocusNode? focusNode;
  final bool autofocus;

  const AppInput({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.errorText,
    this.obscureText = false,
    this.readOnly = false,
    this.keyboardType,
    this.textInputAction,
    this.maxLines = 1,
    this.maxLength,
    this.prefixIcon,
    this.suffixIcon,
    this.onChanged,
    this.onSubmitted,
    this.validator,
    this.focusNode,
    this.autofocus = false,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      readOnly: readOnly,
      keyboardType: keyboardType,
      textInputAction: textInputAction,
      maxLines: maxLines,
      maxLength: maxLength,
      onChanged: onChanged,
      onFieldSubmitted: onSubmitted,
      validator: validator,
      focusNode: focusNode,
      autofocus: autofocus,
      textDirection: TextDirection.rtl,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        errorText: errorText,
        prefixIcon: prefixIcon,
        suffixIcon: suffixIcon,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.base,
          vertical: SpacingTokens.md,
        ),
      ),
    );
  }
}
