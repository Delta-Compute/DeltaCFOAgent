'use client'

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { ptBR } from '@/lib/i18n'
import { formatCurrencyBR } from '@/lib/utils'
import {
  TrendingUp,
  TrendingDown,
  Briefcase,
  DollarSign,
  Clock,
  CheckCircle,
  BarChart3,
} from 'lucide-react'

export default function IndicatorsPage() {
  const t = ptBR
  const [period, setPeriod] = React.useState('month')

  // Mock data
  const stats = {
    totalCases: 42,
    casesChange: 12,
    revenue: 85000,
    revenueChange: 15,
    deadlineCompliance: 94,
    complianceChange: 2,
    avgTaskCompletion: 3.2, // days
    completionChange: -0.5,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.indicators.title}</h1>
          <p className="mt-1 text-gray-500">
            Acompanhe o desempenho do seu escritorio
          </p>
        </div>
        <Select
          options={[
            { value: 'week', label: t.indicators.periodOptions.week },
            { value: 'month', label: t.indicators.periodOptions.month },
            { value: 'quarter', label: t.indicators.periodOptions.quarter },
            { value: 'year', label: t.indicators.periodOptions.year },
          ]}
          value={period}
          onChange={setPeriod}
          className="w-48"
        />
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{t.indicators.caseVolume}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900">{stats.totalCases}</p>
              </div>
              <div className="rounded-lg bg-primary-100 p-3">
                <Briefcase className="h-6 w-6 text-primary-600" />
              </div>
            </div>
            <div className="mt-3 flex items-center text-sm">
              {stats.casesChange > 0 ? (
                <>
                  <TrendingUp className="mr-1 h-4 w-4 text-green-500" />
                  <span className="text-green-600">+{stats.casesChange}%</span>
                </>
              ) : (
                <>
                  <TrendingDown className="mr-1 h-4 w-4 text-red-500" />
                  <span className="text-red-600">{stats.casesChange}%</span>
                </>
              )}
              <span className="ml-1 text-gray-500">vs periodo anterior</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{t.indicators.revenue}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900">
                  {formatCurrencyBR(stats.revenue)}
                </p>
              </div>
              <div className="rounded-lg bg-green-100 p-3">
                <DollarSign className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <div className="mt-3 flex items-center text-sm">
              {stats.revenueChange > 0 ? (
                <>
                  <TrendingUp className="mr-1 h-4 w-4 text-green-500" />
                  <span className="text-green-600">+{stats.revenueChange}%</span>
                </>
              ) : (
                <>
                  <TrendingDown className="mr-1 h-4 w-4 text-red-500" />
                  <span className="text-red-600">{stats.revenueChange}%</span>
                </>
              )}
              <span className="ml-1 text-gray-500">vs periodo anterior</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{t.indicators.deadlineCompliance}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900">
                  {stats.deadlineCompliance}%
                </p>
              </div>
              <div className="rounded-lg bg-blue-100 p-3">
                <CheckCircle className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            <div className="mt-3 flex items-center text-sm">
              {stats.complianceChange > 0 ? (
                <>
                  <TrendingUp className="mr-1 h-4 w-4 text-green-500" />
                  <span className="text-green-600">+{stats.complianceChange}%</span>
                </>
              ) : (
                <>
                  <TrendingDown className="mr-1 h-4 w-4 text-red-500" />
                  <span className="text-red-600">{stats.complianceChange}%</span>
                </>
              )}
              <span className="ml-1 text-gray-500">vs periodo anterior</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{t.indicators.productivity}</p>
                <p className="mt-1 text-3xl font-bold text-gray-900">
                  {stats.avgTaskCompletion} dias
                </p>
              </div>
              <div className="rounded-lg bg-purple-100 p-3">
                <Clock className="h-6 w-6 text-purple-600" />
              </div>
            </div>
            <div className="mt-3 flex items-center text-sm">
              {stats.completionChange < 0 ? (
                <>
                  <TrendingUp className="mr-1 h-4 w-4 text-green-500" />
                  <span className="text-green-600">{Math.abs(stats.completionChange)} dias mais rapido</span>
                </>
              ) : (
                <>
                  <TrendingDown className="mr-1 h-4 w-4 text-red-500" />
                  <span className="text-red-600">{stats.completionChange} dias mais lento</span>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Placeholder */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              {t.indicators.caseVolume} por mes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center text-gray-500">
              Grafico em desenvolvimento...
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              {t.indicators.revenue} por mes
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex h-64 items-center justify-center text-gray-500">
              Grafico em desenvolvimento...
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Win Rate Card */}
      <Card>
        <CardHeader>
          <CardTitle>{t.indicators.winRate}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-green-50 p-4 text-center">
              <p className="text-3xl font-bold text-green-600">28</p>
              <p className="text-sm text-green-700">Processos ganhos</p>
            </div>
            <div className="rounded-lg bg-red-50 p-4 text-center">
              <p className="text-3xl font-bold text-red-600">6</p>
              <p className="text-sm text-red-700">Processos perdidos</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-4 text-center">
              <p className="text-3xl font-bold text-gray-600">8</p>
              <p className="text-sm text-gray-700">Em andamento</p>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Taxa de exito</span>
              <span className="font-semibold text-gray-900">82.4%</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-200">
              <div className="h-full w-[82.4%] bg-green-500" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
