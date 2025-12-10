"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Landmark,
  Wallet as WalletIcon,
  Plus,
  RefreshCw,
  Search,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  CheckCircle2,
  XCircle,
  Copy,
} from "lucide-react";
import { toast } from "sonner";

import {
  bankAccounts,
  wallets,
  type BankAccount,
  type Wallet,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Card, CardContent } from "@/components/ui/card";
import { DataTable, type Column } from "@/components/dashboard/data-table";
import { StatsCard, StatsGrid } from "@/components/dashboard/stats-card";
import { ErrorState } from "@/components/ui/empty-state";

// Account type badge
function AccountTypeBadge({ type }: { type: BankAccount["account_type"] }) {
  const colors: Record<BankAccount["account_type"], string> = {
    checking: "bg-blue-100 text-blue-700",
    savings: "bg-green-100 text-green-700",
    credit: "bg-purple-100 text-purple-700",
    investment: "bg-amber-100 text-amber-700",
    loan: "bg-red-100 text-red-700",
  };

  return (
    <Badge variant="outline" className={colors[type]}>
      {type.charAt(0).toUpperCase() + type.slice(1)}
    </Badge>
  );
}

// Blockchain badge for crypto
function BlockchainBadge({ blockchain }: { blockchain: string }) {
  const colors: Record<string, string> = {
    ethereum: "bg-indigo-100 text-indigo-700",
    bitcoin: "bg-orange-100 text-orange-700",
    polygon: "bg-purple-100 text-purple-700",
    solana: "bg-gradient-to-r from-purple-100 to-green-100 text-purple-700",
  };

  return (
    <Badge variant="outline" className={colors[blockchain.toLowerCase()] || "bg-gray-100 text-gray-700"}>
      {blockchain}
    </Badge>
  );
}

// Stats interfaces
interface BankStats {
  totalAccounts: number;
  activeAccounts: number;
  totalBalance: number;
  byType: Record<string, number>;
}

interface WalletStats {
  totalWallets: number;
  activeWallets: number;
  blockchains: string[];
}

export default function AccountsPage() {
  const [activeTab, setActiveTab] = useState("bank");

  // Bank accounts state
  const [bankAccountsList, setBankAccountsList] = useState<BankAccount[]>([]);
  const [bankStats, setBankStats] = useState<BankStats | null>(null);
  const [isBankLoading, setIsBankLoading] = useState(true);
  const [bankError, setBankError] = useState<string | null>(null);
  const [bankSearch, setBankSearch] = useState("");

  // Wallets state
  const [walletsList, setWalletsList] = useState<Wallet[]>([]);
  const [walletStats, setWalletStats] = useState<WalletStats | null>(null);
  const [isWalletsLoading, setIsWalletsLoading] = useState(true);
  const [walletsError, setWalletsError] = useState<string | null>(null);
  const [walletsSearch, setWalletsSearch] = useState("");

  // Load bank accounts
  const loadBankAccounts = useCallback(async () => {
    setIsBankLoading(true);
    setBankError(null);

    try {
      const result = await bankAccounts.list();

      if (result.success && result.data) {
        // Filter by search if provided
        let filteredAccounts = result.data;
        if (bankSearch) {
          const search = bankSearch.toLowerCase();
          filteredAccounts = result.data.filter(
            (a) =>
              a.account_name.toLowerCase().includes(search) ||
              a.bank_name.toLowerCase().includes(search) ||
              a.account_number.includes(search)
          );
        }

        setBankAccountsList(filteredAccounts);

        // Calculate stats from all data
        const activeAccounts = result.data.filter((a) => a.status === "active").length;
        const totalBalance = result.data.reduce((sum, a) => sum + (a.balance || 0), 0);
        const byType: Record<string, number> = {};
        result.data.forEach((a) => {
          byType[a.account_type] = (byType[a.account_type] || 0) + 1;
        });

        setBankStats({
          totalAccounts: result.data.length,
          activeAccounts,
          totalBalance,
          byType,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load bank accounts");
      }
    } catch (err) {
      console.error("Failed to load bank accounts:", err);
      setBankError(err instanceof Error ? err.message : "Failed to load bank accounts");
    } finally {
      setIsBankLoading(false);
    }
  }, [bankSearch]);

  // Load wallets
  const loadWallets = useCallback(async () => {
    setIsWalletsLoading(true);
    setWalletsError(null);

    try {
      const result = await wallets.list();

      if (result.success && result.data) {
        // Filter by search if provided
        let filteredWallets = result.data;
        if (walletsSearch) {
          const search = walletsSearch.toLowerCase();
          filteredWallets = result.data.filter(
            (w) =>
              w.wallet_name.toLowerCase().includes(search) ||
              w.address.toLowerCase().includes(search) ||
              w.blockchain.toLowerCase().includes(search)
          );
        }

        setWalletsList(filteredWallets);

        // Calculate stats from all data
        const activeWallets = result.data.filter((w) => w.status === "active").length;
        const blockchains = [...new Set(result.data.map((w) => w.blockchain))];

        setWalletStats({
          totalWallets: result.data.length,
          activeWallets,
          blockchains,
        });
      } else {
        throw new Error(result.error?.message || "Failed to load wallets");
      }
    } catch (err) {
      console.error("Failed to load wallets:", err);
      setWalletsError(err instanceof Error ? err.message : "Failed to load wallets");
    } finally {
      setIsWalletsLoading(false);
    }
  }, [walletsSearch]);

  // Load data based on active tab
  useEffect(() => {
    if (activeTab === "bank") {
      loadBankAccounts();
    } else {
      loadWallets();
    }
  }, [activeTab, loadBankAccounts, loadWallets]);

  // Copy address to clipboard
  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  }

  // Delete bank account
  async function handleDeleteBankAccount(account: BankAccount) {
    if (!confirm(`Are you sure you want to delete ${account.account_name}?`)) {
      return;
    }

    try {
      const result = await bankAccounts.delete(account.id);
      if (result.success) {
        toast.success("Account deleted");
        loadBankAccounts();
      } else {
        toast.error(result.error?.message || "Failed to delete account");
      }
    } catch {
      toast.error("Failed to delete account");
    }
  }

  // Delete wallet
  async function handleDeleteWallet(wallet: Wallet) {
    if (!confirm(`Are you sure you want to delete ${wallet.wallet_name}?`)) {
      return;
    }

    try {
      const result = await wallets.delete(wallet.id);
      if (result.success) {
        toast.success("Wallet deleted");
        loadWallets();
      } else {
        toast.error(result.error?.message || "Failed to delete wallet");
      }
    } catch {
      toast.error("Failed to delete wallet");
    }
  }

  // Bank accounts columns
  const bankColumns: Column<BankAccount>[] = [
    {
      key: "account_name",
      header: "Account Name",
      render: (item) => (
        <div>
          <div className="font-medium">{item.account_name}</div>
          <div className="text-xs text-muted-foreground">{item.bank_name}</div>
        </div>
      ),
    },
    {
      key: "account_number",
      header: "Account Number",
      width: "150px",
      render: (item) => (
        <span className="font-mono text-sm">
          ****{item.account_number.slice(-4)}
        </span>
      ),
    },
    {
      key: "account_type",
      header: "Type",
      width: "120px",
      render: (item) => <AccountTypeBadge type={item.account_type} />,
    },
    {
      key: "balance",
      header: "Balance",
      align: "right",
      render: (item) => (
        <span className="font-medium">
          {item.balance !== undefined ? formatCurrency(item.balance, item.currency) : "-"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "100px",
      render: (item) => (
        <Badge
          variant={item.status === "active" ? "default" : "outline"}
          className="gap-1"
        >
          {item.status === "active" ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <XCircle className="h-3 w-3" />
          )}
          {item.status}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      width: "50px",
      render: (item) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => handleDeleteBankAccount(item)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  // Wallets columns
  const walletColumns: Column<Wallet>[] = [
    {
      key: "wallet_name",
      header: "Wallet",
      render: (item) => (
        <div>
          <div className="font-medium">{item.wallet_name}</div>
          <div className="text-xs text-muted-foreground truncate max-w-[200px]">
            {item.address}
          </div>
        </div>
      ),
    },
    {
      key: "address",
      header: "Address",
      render: (item) => (
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm truncate max-w-[150px]">
            {item.address.slice(0, 8)}...{item.address.slice(-6)}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => copyToClipboard(item.address)}
          >
            <Copy className="h-3 w-3" />
          </Button>
        </div>
      ),
    },
    {
      key: "blockchain",
      header: "Blockchain",
      width: "120px",
      render: (item) => <BlockchainBadge blockchain={item.blockchain} />,
    },
    {
      key: "status",
      header: "Status",
      width: "100px",
      render: (item) => (
        <Badge
          variant={item.status === "active" ? "default" : "outline"}
          className="gap-1"
        >
          {item.status === "active" ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <XCircle className="h-3 w-3" />
          )}
          {item.status}
        </Badge>
      ),
    },
    {
      key: "created_at",
      header: "Added",
      width: "100px",
      render: (item) => (
        <span className="text-sm text-muted-foreground">
          {formatDate(item.created_at)}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      width: "50px",
      render: (item) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => handleDeleteWallet(item)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold font-heading">Whitelisted Accounts</h1>
          <p className="text-muted-foreground">
            Manage your bank accounts and crypto wallets
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={activeTab === "bank" ? loadBankAccounts : loadWallets}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            {activeTab === "bank" ? "Add Account" : "Add Wallet"}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="bank" className="gap-2">
            <Landmark className="h-4 w-4" />
            Bank Accounts
          </TabsTrigger>
          <TabsTrigger value="crypto" className="gap-2">
            <WalletIcon className="h-4 w-4" />
            Crypto Wallets
          </TabsTrigger>
        </TabsList>

        {/* Bank Accounts Tab */}
        <TabsContent value="bank" className="space-y-6">
          {/* Stats */}
          <StatsGrid>
            <StatsCard
              title="Total Accounts"
              value={bankStats?.totalAccounts.toLocaleString() || "0"}
              icon={Landmark}
              isLoading={isBankLoading}
            />
            <StatsCard
              title="Active"
              value={bankStats?.activeAccounts.toLocaleString() || "0"}
              icon={CheckCircle2}
              isLoading={isBankLoading}
            />
            <StatsCard
              title="Total Balance"
              value={formatCurrency(bankStats?.totalBalance || 0)}
              icon={Landmark}
              isLoading={isBankLoading}
            />
            <StatsCard
              title="Account Types"
              value={Object.keys(bankStats?.byType || {}).length.toString()}
              icon={Landmark}
              isLoading={isBankLoading}
            />
          </StatsGrid>

          {/* Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search accounts..."
                  value={bankSearch}
                  onChange={(e) => setBankSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          {bankError ? (
            <ErrorState title={bankError} onRetry={loadBankAccounts} />
          ) : (
            <DataTable
              columns={bankColumns}
              data={bankAccountsList}
              keyField="id"
              isLoading={isBankLoading}
              emptyMessage="No bank accounts found"
            />
          )}
        </TabsContent>

        {/* Crypto Wallets Tab */}
        <TabsContent value="crypto" className="space-y-6">
          {/* Stats */}
          <StatsGrid>
            <StatsCard
              title="Total Wallets"
              value={walletStats?.totalWallets.toLocaleString() || "0"}
              icon={WalletIcon}
              isLoading={isWalletsLoading}
            />
            <StatsCard
              title="Active"
              value={walletStats?.activeWallets.toLocaleString() || "0"}
              icon={CheckCircle2}
              isLoading={isWalletsLoading}
            />
            <StatsCard
              title="Blockchains"
              value={walletStats?.blockchains.length.toString() || "0"}
              icon={WalletIcon}
              isLoading={isWalletsLoading}
            />
            <StatsCard
              title="Top Blockchain"
              value={walletStats?.blockchains[0] || "-"}
              icon={WalletIcon}
              isLoading={isWalletsLoading}
            />
          </StatsGrid>

          {/* Search */}
          <Card>
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search wallets..."
                  value={walletsSearch}
                  onChange={(e) => setWalletsSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          {walletsError ? (
            <ErrorState title={walletsError} onRetry={loadWallets} />
          ) : (
            <DataTable
              columns={walletColumns}
              data={walletsList}
              keyField="id"
              isLoading={isWalletsLoading}
              emptyMessage="No crypto wallets found"
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
