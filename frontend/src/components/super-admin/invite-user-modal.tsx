'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { superAdmin, CreateSuperAdminInvitationData } from '@/lib/api';
import { Loader2, UserPlus, Building2, Briefcase } from 'lucide-react';

interface InviteUserModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function InviteUserModal({ open, onOpenChange, onSuccess }: InviteUserModalProps) {
  const [email, setEmail] = useState('');
  const [userType, setUserType] = useState<'fractional_cfo' | 'tenant_admin'>('fractional_cfo');
  const [companyName, setCompanyName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setEmail('');
    setUserType('fractional_cfo');
    setCompanyName('');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!email) {
      setError('Email is required');
      return;
    }

    if (!email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    if (userType === 'tenant_admin' && !companyName.trim()) {
      setError('Company name is required for Business Owners');
      return;
    }

    setIsSubmitting(true);

    try {
      const data: CreateSuperAdminInvitationData = {
        email,
        user_type: userType,
      };

      if (userType === 'tenant_admin') {
        data.company_name = companyName.trim();
      }

      const response = await superAdmin.createInvitation(data);

      if (response.success && response.data?.success) {
        resetForm();
        onOpenChange(false);
        onSuccess?.();
      } else {
        const errorMessage = response.error?.message ||
          (response.data as { message?: string })?.message ||
          'Failed to send invitation';
        setError(errorMessage);
      }
    } catch (err) {
      console.error('Failed to create invitation:', err);
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      resetForm();
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Invite New User
          </DialogTitle>
          <DialogDescription>
            Send an invitation to a new CFO or Business Owner to join Delta CFO Agent.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* User Type Selection */}
            <div className="grid gap-2">
              <Label htmlFor="user-type">User Type</Label>
              <Select
                value={userType}
                onValueChange={(value: 'fractional_cfo' | 'tenant_admin') => {
                  setUserType(value);
                  setError(null);
                }}
              >
                <SelectTrigger id="user-type">
                  <SelectValue placeholder="Select user type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="fractional_cfo">
                    <div className="flex items-center gap-2">
                      <Briefcase className="h-4 w-4" />
                      <span>Fractional CFO</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="tenant_admin">
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4" />
                      <span>Business Owner</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-zinc-500">
                {userType === 'fractional_cfo'
                  ? 'CFOs can create and manage multiple client companies'
                  : 'Business Owners will have their own company tenant created'}
              </p>
            </div>

            {/* Email Input */}
            <div className="grid gap-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setError(null);
                }}
                disabled={isSubmitting}
              />
            </div>

            {/* Company Name (only for Business Owners) */}
            {userType === 'tenant_admin' && (
              <div className="grid gap-2">
                <Label htmlFor="company-name">Company Name</Label>
                <Input
                  id="company-name"
                  type="text"
                  placeholder="Acme Corporation"
                  value={companyName}
                  onChange={(e) => {
                    setCompanyName(e.target.value);
                    setError(null);
                  }}
                  disabled={isSubmitting}
                />
                <p className="text-xs text-zinc-500">
                  This will be used as the tenant name for their company
                </p>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Send Invitation
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
