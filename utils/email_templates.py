"""
Modern, responsive email templates for PathtoForever Dating
"""


def get_email_base_template(content: str) -> str:
    """Base email template with modern styling and responsive design"""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>PathtoForever</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: #f9fafb;
            color: #111827;
        }}
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        .header {{
            background: linear-gradient(135deg, #A11013 0%, #d946a6 100%);
            padding: 40px 20px;
            text-align: center;
        }}
        .logo {{
            font-size: 32px;
            font-weight: bold;
            color: #ffffff;
            margin: 0;
            letter-spacing: -0.5px;
        }}
        .tagline {{
            color: #fce7f3;
            font-size: 14px;
            margin-top: 8px;
        }}
        .content {{
            padding: 40px 30px;
        }}
        .greeting {{
            font-size: 24px;
            font-weight: 700;
            color: #111827;
            margin: 0 0 20px 0;
        }}
        .message {{
            font-size: 16px;
            line-height: 1.6;
            color: #4b5563;
            margin: 0 0 20px 0;
        }}
        .highlight {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 16px;
            margin: 24px 0;
            border-radius: 8px;
        }}
        .highlight-text {{
            font-size: 18px;
            font-weight: 600;
            color: #92400e;
            margin: 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #A11013 0%, #d946a6 100%);
            color: #ffffff !important;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            margin: 24px 0;
            box-shadow: 0 4px 6px rgba(161, 16, 19, 0.2);
            transition: all 0.3s ease;
        }}
        .button:hover {{
            box-shadow: 0 6px 12px rgba(161, 16, 19, 0.3);
        }}
        .features {{
            background-color: #fef2f2;
            border-radius: 12px;
            padding: 24px;
            margin: 24px 0;
        }}
        .features-title {{
            font-size: 18px;
            font-weight: 600;
            color: #991b1b;
            margin: 0 0 16px 0;
        }}
        .feature-item {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            font-size: 15px;
            color: #4b5563;
        }}
        .feature-icon {{
            margin-right: 12px;
            font-size: 20px;
        }}
        .footer {{
            background-color: #f9fafb;
            padding: 30px 20px;
            text-align: center;
            border-top: 1px solid #e5e7eb;
        }}
        .footer-text {{
            font-size: 14px;
            color: #6b7280;
            margin: 8px 0;
        }}
        .footer-link {{
            color: #A11013;
            text-decoration: none;
        }}
        .divider {{
            height: 1px;
            background-color: #e5e7eb;
            margin: 30px 0;
        }}
        @media only screen and (max-width: 600px) {{
            .content {{
                padding: 30px 20px;
            }}
            .greeting {{
                font-size: 20px;
            }}
            .button {{
                display: block;
                text-align: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1 class="logo">💕 PathtoForever</h1>
            <p class="tagline">Find Your Perfect Match</p>
        </div>
        {content}
        <div class="footer">
            <p class="footer-text">
                <strong>PathtoForever Dating</strong><br>
                AI-Powered Matchmaking Platform
            </p>
            <p class="footer-text">
                Need help? <a href="mailto:support@PathtoForever.com" class="footer-link">Contact Support</a>
            </p>
            <p class="footer-text" style="font-size: 12px; color: #9ca3af; margin-top: 16px;">
                You're receiving this email because you have an active PathtoForever account.<br>
                © 2025 PathtoForever. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
"""


def get_payment_success_email(plan_name: str, expires_at: str, renew_url: str) -> str:
    """Email template for successful payment confirmation"""
    content = f"""
        <div class="content">
            <h2 class="greeting">🎉 Payment Successful!</h2>
            <p class="message">
                Congratulations! Your <strong>{plan_name}</strong> plan is now active. 
                You now have full access to all premium features.
            </p>
            
            <div class="features">
                <p class="features-title">✨ Your Premium Benefits:</p>
                <div class="feature-item">
                    <span class="feature-icon">💕</span>
                    <span>Unlimited matches and likes</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">💬</span>
                    <span>Send unlimited messages</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🤖</span>
                    <span>AI-powered match suggestions</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⚡</span>
                    <span>Priority profile visibility</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">👑</span>
                    <span>Premium badge on your profile</span>
                </div>
            </div>
            
            <div class="highlight">
                <p class="highlight-text">
                    📅 Your access expires on: {expires_at}
                </p>
            </div>
            
            <p class="message">
                Since you paid via mobile money, you'll need to manually renew when your plan expires. 
                Don't worry—we'll send you a reminder email a few days before.
            </p>
            
            <div style="text-align: center;">
                <a href="{renew_url}" class="button">Start Matching Now →</a>
            </div>
            
            <div class="divider"></div>
            
            <p class="message" style="font-size: 14px; color: #6b7280;">
                <strong>Need to renew?</strong> Simply visit the subscribe page and complete the payment again. 
                It's quick and easy!
            </p>
        </div>
    """
    return get_email_base_template(content)


def get_renewal_reminder_email(expires_at: str, renew_url: str, days_left: int) -> str:
    """Email template for renewal reminders"""
    urgency_color = "#dc2626" if days_left <= 1 else "#f59e0b"
    urgency_bg = "#fef2f2" if days_left <= 1 else "#fef3c7"
    
    content = f"""
        <div class="content">
            <h2 class="greeting">⏰ Your Premium is Expiring Soon</h2>
            <p class="message">
                We wanted to remind you that your PathtoForever Premium access is about to expire. 
                Don't miss out on connecting with amazing people!
            </p>
            
            <div class="highlight" style="background-color: {urgency_bg}; border-left-color: {urgency_color};">
                <p class="highlight-text" style="color: {urgency_color};">
                    ⚠️ Expires on: {expires_at}
                </p>
            </div>
            
            <p class="message">
                <strong>What happens when your premium expires?</strong>
            </p>
            <p class="message" style="margin-top: 12px;">
                • You'll lose access to unlimited matches<br>
                • Your messages will be limited<br>
                • AI match suggestions will stop<br>
                • Your profile visibility will decrease
            </p>
            
            <div style="text-align: center; margin: 32px 0;">
                <a href="{renew_url}" class="button">Renew Premium Now →</a>
            </div>
            
            <div class="features">
                <p class="features-title">💎 Keep Your Premium Benefits:</p>
                <div class="feature-item">
                    <span class="feature-icon">✅</span>
                    <span>Continue unlimited matching</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✅</span>
                    <span>Keep your conversations going</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">✅</span>
                    <span>Maintain priority visibility</span>
                </div>
            </div>
            
            <p class="message" style="margin-top: 24px;">
                Renewing is easy! Just click the button above, select your plan, and complete the payment. 
                Your premium access will continue seamlessly.
            </p>
            
            <div class="divider"></div>
            
            <p class="message" style="font-size: 14px; color: #6b7280; text-align: center;">
                Questions? We're here to help! Reply to this email or contact our support team.
            </p>
        </div>
    """
    return get_email_base_template(content)


def get_card_subscription_welcome_email(plan_name: str, next_billing_date: str) -> str:
    """Email template for card subscription activation"""
    content = f"""
        <div class="content">
            <h2 class="greeting">🎉 Welcome to PathtoForever Premium!</h2>
            <p class="message">
                Your <strong>{plan_name}</strong> subscription is now active! 
                Your card will be automatically charged for renewal, so you never have to worry about losing access.
            </p>
            
            <div class="features">
                <p class="features-title">✨ Your Premium Benefits:</p>
                <div class="feature-item">
                    <span class="feature-icon">💕</span>
                    <span>Unlimited matches and likes</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">💬</span>
                    <span>Send unlimited messages</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🤖</span>
                    <span>AI-powered match suggestions</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⚡</span>
                    <span>Priority profile visibility</span>
                </div>
            </div>
            
            <div class="highlight">
                <p class="highlight-text">
                    🔄 Next billing date: {next_billing_date}
                </p>
            </div>
            
            <p class="message">
                Your subscription will automatically renew. You can cancel anytime from your account settings.
            </p>
            
            <div style="text-align: center;">
                <a href="https://www.pathtoforever.com/discover" class="button">Start Matching Now →</a>
            </div>
        </div>
    """
    return get_email_base_template(content)
