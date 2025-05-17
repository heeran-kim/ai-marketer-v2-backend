from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, EmailConfiguration  # We'll add EmailConfiguration to your models

class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'role')
    search_fields = ('email', 'name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Two-Factor Authentication', {'fields': ('requires_2fa', 'secret_2fa')}),
        ('Permissions', {'fields': ('groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )

admin.site.register(User, UserAdmin)

class EmailConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_host_user', 'email_host', 'is_active', 'updated_at')
    list_filter = ('is_active', 'email_use_tls')
    search_fields = ('name', 'email_host_user', 'email_host')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'is_active'),
        }),
        ('Email Server Settings', {
            'fields': ('email_backend', 'email_host', 'email_port', 'email_use_tls'),
        }),
        ('Authentication', {
            'fields': ('email_host_user', 'email_host_password', 'default_from_email'),
        }),
    )
    
    actions = ['test_email_config']
    
    def test_email_config(self, request, queryset):
        from django.core.mail import send_mail
        
        for config in queryset:
            # Temporarily set this config as active
            old_active = EmailConfiguration.objects.filter(is_active=True).first()
            config.is_active = True
            config.save()
            
            try:
                send_mail(
                    'Test Email Configuration',
                    'This is a test email from your Django application.',
                    None,  # Uses DEFAULT_FROM_EMAIL from the configuration
                    [request.user.email],
                    fail_silently=False,
                )
                self.message_user(request, f"Test email sent successfully using '{config.name}'")
            except Exception as e:
                self.message_user(request, f"Error sending test email using '{config.name}': {str(e)}")
                
            # Restore the old active config if there was one
            if old_active and old_active.pk != config.pk:
                old_active.is_active = True
                old_active.save()
    
    test_email_config.short_description = "Test selected email configurations"

# Register the EmailConfiguration model with the admin site
admin.site.register(EmailConfiguration, EmailConfigurationAdmin)