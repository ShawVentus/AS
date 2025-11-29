-- Update handle_new_user function to extract username from metadata
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (user_id, info, focus, context, memory)
  VALUES (
    NEW.id::text,
    jsonb_build_object(
      'email', NEW.email,
      'name', COALESCE(NEW.raw_user_meta_data->>'username', NEW.email),
      'nickname', COALESCE(NEW.raw_user_meta_data->>'username', ''),
      'avatar', ''
    ),
    '{}'::jsonb,
    '{}'::jsonb,
    '{}'::jsonb
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
