# Amazon Cognito Authentication Setup

This document provides instructions for setting up Amazon Cognito authentication for the Sports Marketing Video Generator application.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with your credentials
- Basic knowledge of AWS Cognito

## Step 1: Create a Cognito User Pool

1. Go to the AWS Management Console and navigate to Amazon Cognito
2. Click "Create user pool"
3. Configure sign-in experience:
   - Select "Email" as a sign-in option
   - Choose Cognito defaults for password policy or customize as needed
4. Configure security requirements:
   - Choose MFA settings based on your security needs
   - Select password recovery method (email recommended)
5. Configure sign-up experience:
   - Select required attributes (email is recommended)
   - Choose self-service sign-up option if you want users to register themselves
6. Configure message delivery:
   - Use Cognito's default email provider or configure your own SES
7. Integrate your app:
   - Enter a User Pool name (e.g., "SportsMarketingApp")
   - Create an app client with a descriptive name (e.g., "sports-marketing-web-client")
   - Select "Generate a client secret" option
8. Review and create the user pool

## Step 2: Configure App Client Settings

1. In your newly created User Pool, go to "App integration" tab
2. Under "App client settings", find your app client
3. Configure the following:
   - Enable Cognito Hosted UI
   - Configure a domain name (either use a Cognito domain or your custom domain)
   - Set Callback URL(s) to your application URL (e.g., `http://localhost:8501/` for local development)
   - Set Sign out URL(s) to your application URL
   - Select "Authorization code grant" flow
   - Select "email", "openid", and "profile" for OAuth scopes

## Step 3: Configure Environment Variables

Set the following environment variables in your application environment:

```bash
export COGNITO_USER_POOL_ID=your-user-pool-id
export COGNITO_APP_CLIENT_ID=your-app-client-id
export COGNITO_APP_CLIENT_SECRET=your-app-client-secret
export COGNITO_DOMAIN=your-cognito-domain.auth.region.amazoncognito.com
export COGNITO_REDIRECT_URI=http://localhost:8501/
```

For production, ensure these are set in your deployment environment.

## Step 4: Create Test Users

1. In your User Pool, go to "Users" tab
2. Click "Create user"
3. Fill in the required information
4. Choose whether to send an invitation to the user
5. Click "Create user"

## Testing Authentication

1. Start your application
2. You should be redirected to the Cognito Hosted UI login page
3. Enter the credentials for a test user
4. After successful authentication, you'll be redirected back to your application

## Troubleshooting

- **Redirect URI Mismatch**: Ensure the redirect URI in your Cognito app client settings exactly matches the one in your environment variables
- **CORS Issues**: If you encounter CORS errors, check that your domain is properly configured in the Cognito settings
- **Token Errors**: Verify that your client ID and secret are correct

## Security Considerations

- Always use HTTPS in production
- Implement proper token storage and refresh mechanisms
- Consider implementing MFA for enhanced security
- Regularly rotate client secrets
- Set appropriate token expiration times