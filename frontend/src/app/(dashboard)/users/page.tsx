"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Users,
  Search,
  RefreshCw,
  Edit,
  Trash2,
  MoreHorizontal,
  Mail,
  Shield,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  UserPlus,
  Send,
} from "lucide-react";
import { toast } from "sonner";

import {
  users,
  type TenantUser,
  type UserInvitation,
  type InviteUserData,
} from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { ErrorState, LoadingState } from "@/components/ui/empty-state";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";

// Available roles
const roles = [
  { value: "admin", label: "Admin" },
  { value: "manager", label: "Manager" },
  { value: "analyst", label: "Analyst" },
  { value: "viewer", label: "Viewer" },
];

// Available permissions
const permissionGroups = [
  {
    name: "Transactions",
    permissions: [
      { key: "transactions.view", label: "View" },
      { key: "transactions.create", label: "Create" },
      { key: "transactions.edit", label: "Edit" },
      { key: "transactions.delete", label: "Delete" },
    ],
  },
  {
    name: "Invoices",
    permissions: [
      { key: "invoices.view", label: "View" },
      { key: "invoices.create", label: "Create" },
      { key: "invoices.edit", label: "Edit" },
      { key: "invoices.approve", label: "Approve" },
    ],
  },
  {
    name: "Reports",
    permissions: [
      { key: "reports.view", label: "View" },
      { key: "reports.generate", label: "Generate" },
      { key: "reports.export", label: "Export" },
    ],
  },
  {
    name: "Users",
    permissions: [
      { key: "users.view", label: "View" },
      { key: "users.invite", label: "Invite" },
      { key: "users.manage", label: "Manage" },
    ],
  },
];

// User type badge
function UserTypeBadge({
  type,
}: {
  type: TenantUser["user_type"];
}) {
  const config: Record<
    TenantUser["user_type"],
    { label: string; variant: "default" | "secondary" | "outline" }
  > = {
    fractional_cfo: { label: "Fractional CFO", variant: "default" },
    cfo_assistant: { label: "CFO Assistant", variant: "secondary" },
    tenant_admin: { label: "Admin", variant: "default" },
    employee: { label: "Employee", variant: "outline" },
  };

  const { label, variant } = config[type] || { label: type, variant: "outline" };

  return <Badge variant={variant}>{label}</Badge>;
}

// Status badge
function StatusBadge({ status }: { status: TenantUser["status"] }) {
  const config: Record<
    TenantUser["status"],
    { label: string; icon: typeof CheckCircle2; className: string }
  > = {
    active: {
      label: "Active",
      icon: CheckCircle2,
      className: "text-green-600",
    },
    inactive: {
      label: "Inactive",
      icon: XCircle,
      className: "text-gray-500",
    },
    pending: {
      label: "Pending",
      icon: Clock,
      className: "text-yellow-600",
    },
  };

  const { label, icon: Icon, className } = config[status];

  return (
    <span className={cn("flex items-center gap-1 text-sm", className)}>
      <Icon className="h-4 w-4" />
      {label}
    </span>
  );
}

export default function UsersPage() {
  // State
  const [userList, setUserList] = useState<TenantUser[]>([]);
  const [invitations, setInvitations] = useState<UserInvitation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("users");

  // Filters
  const [search, setSearch] = useState("");

  // Dialogs
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState<TenantUser | null>(null);

  // Form state
  const [inviteData, setInviteData] = useState<InviteUserData>({
    email: "",
    name: "",
    user_type: "employee",
    role: "viewer",
    permissions: [],
  });
  const [editPermissions, setEditPermissions] = useState<string[]>([]);
  const [editRole, setEditRole] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load data
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [usersResult, invitationsResult] = await Promise.all([
        users.list(),
        users.getPendingInvitations(),
      ]);

      if (usersResult.success && usersResult.data) {
        setUserList(usersResult.data.users);
      }

      if (invitationsResult.success && invitationsResult.data) {
        setInvitations(invitationsResult.data);
      }
    } catch (err) {
      console.error("Failed to load users:", err);
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter users
  const filteredUsers = userList.filter(
    (user) =>
      search === "" ||
      user.name.toLowerCase().includes(search.toLowerCase()) ||
      user.email.toLowerCase().includes(search.toLowerCase())
  );

  // Stats
  const stats = {
    total: userList.length,
    active: userList.filter((u) => u.status === "active").length,
    pending: invitations.filter((i) => i.status === "pending").length,
    admins: userList.filter(
      (u) => u.user_type === "tenant_admin" || u.user_type === "fractional_cfo"
    ).length,
  };

  // Invite user
  async function handleInvite() {
    setIsSubmitting(true);
    try {
      const result = await users.invite(inviteData);
      if (result.success) {
        toast.success("Invitation sent successfully");
        setShowInviteDialog(false);
        resetInviteForm();
        loadData();
      } else {
        toast.error(result.error?.message || "Failed to send invitation");
      }
    } catch {
      toast.error("Failed to send invitation");
    } finally {
      setIsSubmitting(false);
    }
  }

  // Update user role
  async function handleUpdateRole() {
    if (!selectedUser) return;
    setIsSubmitting(true);
    try {
      const result = await users.updateRole(
        selectedUser.id,
        editRole,
        editPermissions
      );
      if (result.success) {
        toast.success("User role updated successfully");
        setShowEditDialog(false);
        setSelectedUser(null);
        loadData();
      } else {
        toast.error(result.error?.message || "Failed to update user");
      }
    } catch {
      toast.error("Failed to update user");
    } finally {
      setIsSubmitting(false);
    }
  }

  // Remove user
  async function handleRemove() {
    if (!selectedUser) return;
    setIsSubmitting(true);
    try {
      const result = await users.remove(selectedUser.id);
      if (result.success) {
        toast.success("User removed successfully");
        setShowRemoveDialog(false);
        setSelectedUser(null);
        loadData();
      } else {
        toast.error(result.error?.message || "Failed to remove user");
      }
    } catch {
      toast.error("Failed to remove user");
    } finally {
      setIsSubmitting(false);
    }
  }

  // Resend invitation
  async function handleResendInvitation(invitation: UserInvitation) {
    try {
      const result = await users.resendInvitation(invitation.id);
      if (result.success) {
        toast.success("Invitation resent");
      } else {
        toast.error(result.error?.message || "Failed to resend invitation");
      }
    } catch {
      toast.error("Failed to resend invitation");
    }
  }

  // Cancel invitation
  async function handleCancelInvitation(invitation: UserInvitation) {
    try {
      const result = await users.cancelInvitation(invitation.id);
      if (result.success) {
        toast.success("Invitation cancelled");
        loadData();
      } else {
        toast.error(result.error?.message || "Failed to cancel invitation");
      }
    } catch {
      toast.error("Failed to cancel invitation");
    }
  }

  // Open edit dialog
  function openEditDialog(user: TenantUser) {
    setSelectedUser(user);
    setEditRole(user.role);
    setEditPermissions(user.permissions);
    setShowEditDialog(true);
  }

  // Open remove dialog
  function openRemoveDialog(user: TenantUser) {
    setSelectedUser(user);
    setShowRemoveDialog(true);
  }

  // Reset invite form
  function resetInviteForm() {
    setInviteData({
      email: "",
      name: "",
      user_type: "employee",
      role: "viewer",
      permissions: [],
    });
  }

  // Toggle permission
  function togglePermission(permission: string, isInvite: boolean) {
    if (isInvite) {
      setInviteData((prev) => ({
        ...prev,
        permissions: prev.permissions.includes(permission)
          ? prev.permissions.filter((p) => p !== permission)
          : [...prev.permissions, permission],
      }));
    } else {
      setEditPermissions((prev) =>
        prev.includes(permission)
          ? prev.filter((p) => p !== permission)
          : [...prev, permission]
      );
    }
  }

  if (isLoading) {
    return <LoadingState message="Loading users..." />;
  }

  if (error) {
    return (
      <ErrorState
        title="Failed to load users"
        description={error}
        onRetry={loadData}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Users</h1>
          <p className="text-muted-foreground">
            Manage user access and permissions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button
            onClick={() => {
              resetInviteForm();
              setShowInviteDialog(true);
            }}
          >
            <UserPlus className="mr-2 h-4 w-4" />
            Invite User
          </Button>
        </div>
      </div>

      {/* Stats */}
      <StatsGrid>
        <StatsCard
          title="Total Users"
          value={stats.total.toString()}
          icon={Users}
        />
        <StatsCard
          title="Active Users"
          value={stats.active.toString()}
          icon={CheckCircle2}
        />
        <StatsCard
          title="Pending Invitations"
          value={stats.pending.toString()}
          icon={Mail}
        />
        <StatsCard
          title="Admins"
          value={stats.admins.toString()}
          icon={Shield}
        />
      </StatsGrid>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="users" className="gap-2">
            <Users className="h-4 w-4" />
            Users ({userList.length})
          </TabsTrigger>
          <TabsTrigger value="invitations" className="gap-2">
            <Mail className="h-4 w-4" />
            Invitations ({invitations.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-4">
          {/* Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search users..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Users Table */}
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Login</TableHead>
                    <TableHead className="w-[50px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="text-center text-muted-foreground py-8"
                      >
                        No users found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredUsers.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{user.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {user.email}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <UserTypeBadge type={user.user_type} />
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{user.role}</Badge>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={user.status} />
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {user.last_login
                            ? formatDate(user.last_login)
                            : "Never"}
                        </TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={() => openEditDialog(user)}
                              >
                                <Edit className="mr-2 h-4 w-4" />
                                Edit Permissions
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => openRemoveDialog(user)}
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Remove
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="invitations" className="space-y-4">
          {/* Invitations Table */}
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Invitee</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="w-[100px]" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invitations.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="text-center text-muted-foreground py-8"
                      >
                        No pending invitations
                      </TableCell>
                    </TableRow>
                  ) : (
                    invitations.map((invitation) => (
                      <TableRow key={invitation.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{invitation.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {invitation.email}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {invitation.user_type}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{invitation.role}</Badge>
                        </TableCell>
                        <TableCell>
                          <span
                            className={cn(
                              "flex items-center gap-1 text-sm",
                              invitation.status === "pending"
                                ? "text-yellow-600"
                                : invitation.status === "expired"
                                ? "text-red-600"
                                : "text-green-600"
                            )}
                          >
                            {invitation.status === "pending" ? (
                              <Clock className="h-4 w-4" />
                            ) : invitation.status === "expired" ? (
                              <XCircle className="h-4 w-4" />
                            ) : (
                              <CheckCircle2 className="h-4 w-4" />
                            )}
                            {invitation.status}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(invitation.expires_at)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => handleResendInvitation(invitation)}
                              title="Resend invitation"
                            >
                              <Send className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive"
                              onClick={() => handleCancelInvitation(invitation)}
                              title="Cancel invitation"
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Invite Dialog */}
      <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Invite User</DialogTitle>
            <DialogDescription>
              Send an invitation to join your organization
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="invite-name">Name *</Label>
                <Input
                  id="invite-name"
                  placeholder="John Doe"
                  value={inviteData.name}
                  onChange={(e) =>
                    setInviteData({ ...inviteData, name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email *</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="john@example.com"
                  value={inviteData.email}
                  onChange={(e) =>
                    setInviteData({ ...inviteData, email: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="invite-type">User Type *</Label>
                <Select
                  value={inviteData.user_type}
                  onValueChange={(value) =>
                    setInviteData({
                      ...inviteData,
                      user_type: value as InviteUserData["user_type"],
                    })
                  }
                >
                  <SelectTrigger id="invite-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="employee">Employee</SelectItem>
                    <SelectItem value="cfo_assistant">CFO Assistant</SelectItem>
                    <SelectItem value="tenant_admin">Tenant Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-role">Role *</Label>
                <Select
                  value={inviteData.role}
                  onValueChange={(value) =>
                    setInviteData({ ...inviteData, role: value })
                  }
                >
                  <SelectTrigger id="invite-role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        {role.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Permissions</Label>
              <div className="border rounded-lg p-4 space-y-4 max-h-[200px] overflow-y-auto">
                {permissionGroups.map((group) => (
                  <div key={group.name}>
                    <p className="text-sm font-medium mb-2">{group.name}</p>
                    <div className="flex flex-wrap gap-3">
                      {group.permissions.map((perm) => (
                        <label
                          key={perm.key}
                          className="flex items-center gap-2 text-sm"
                        >
                          <Checkbox
                            checked={inviteData.permissions.includes(perm.key)}
                            onCheckedChange={() =>
                              togglePermission(perm.key, true)
                            }
                          />
                          {perm.label}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowInviteDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleInvite}
              disabled={
                isSubmitting || !inviteData.email || !inviteData.name
              }
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Mail className="mr-2 h-4 w-4" />
              )}
              Send Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Permissions Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit User Permissions</DialogTitle>
            <DialogDescription>
              Update role and permissions for {selectedUser?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-role">Role</Label>
              <Select value={editRole} onValueChange={setEditRole}>
                <SelectTrigger id="edit-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Permissions</Label>
              <div className="border rounded-lg p-4 space-y-4 max-h-[250px] overflow-y-auto">
                {permissionGroups.map((group) => (
                  <div key={group.name}>
                    <p className="text-sm font-medium mb-2">{group.name}</p>
                    <div className="flex flex-wrap gap-3">
                      {group.permissions.map((perm) => (
                        <label
                          key={perm.key}
                          className="flex items-center gap-2 text-sm"
                        >
                          <Checkbox
                            checked={editPermissions.includes(perm.key)}
                            onCheckedChange={() =>
                              togglePermission(perm.key, false)
                            }
                          />
                          {perm.label}
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowEditDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button onClick={handleUpdateRole} disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle2 className="mr-2 h-4 w-4" />
              )}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Remove User Dialog */}
      <Dialog open={showRemoveDialog} onOpenChange={setShowRemoveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove User</DialogTitle>
            <DialogDescription>
              Are you sure you want to remove {selectedUser?.name} from this
              organization? They will lose access to all resources.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRemoveDialog(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleRemove}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Remove User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
