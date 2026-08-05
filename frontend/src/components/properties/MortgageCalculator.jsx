import { useState, useMemo } from 'react';
import { Calculator, ChevronDown, ChevronUp } from 'lucide-react';
import Card from '../ui/Card';

function calculateMonthlyPayment(principal, annualRate, years) {
  const monthlyRate = annualRate / 100 / 12;
  const totalPayments = years * 12;

  if (monthlyRate === 0) {
    return principal / totalPayments;
  }

  const factor = Math.pow(1 + monthlyRate, totalPayments);
  return principal * (monthlyRate * factor) / (factor - 1);
}

export default function MortgageCalculator({ propertyPrice }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [price, setPrice] = useState(propertyPrice || 0);
  const [downPaymentPercent, setDownPaymentPercent] = useState(30);
  const [interestRate, setInterestRate] = useState(12);
  const [termYears, setTermYears] = useState(20);

  const results = useMemo(() => {
    const downPayment = price * (downPaymentPercent / 100);
    const loanAmount = price - downPayment;
    const monthlyPayment = calculateMonthlyPayment(loanAmount, interestRate, termYears);
    const totalPayment = monthlyPayment * termYears * 12;
    const totalInterest = totalPayment - loanAmount;

    return { downPayment, loanAmount, monthlyPayment, totalPayment, totalInterest };
  }, [price, downPaymentPercent, interestRate, termYears]);

  const formatCOP = (value) =>
    new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(value);

  return (
    <Card className="overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
            <Calculator className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Calculadora de Crédito</h2>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="px-6 pb-6 border-t border-gray-100">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Precio de la propiedad
                </label>
                <input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Cuota inicial ({downPaymentPercent}%)
                </label>
                <input
                  type="range"
                  min="0"
                  max="50"
                  step="5"
                  value={downPaymentPercent}
                  onChange={(e) => setDownPaymentPercent(Number(e.target.value))}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>0%</span>
                  <span>50%</span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tasa de interés anual (%)
                </label>
                <input
                  type="number"
                  value={interestRate}
                  onChange={(e) => setInterestRate(Number(e.target.value))}
                  step="0.1"
                  min="1"
                  max="30"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Plazo ({termYears} años)
                </label>
                <input
                  type="range"
                  min="5"
                  max="30"
                  step="1"
                  value={termYears}
                  onChange={(e) => setTermYears(Number(e.target.value))}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>5 años</span>
                  <span>30 años</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-primary/5 rounded-xl border border-primary/10">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Cuota inicial</p>
                <p className="text-lg font-bold text-gray-900">{formatCOP(results.downPayment)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Monto del crédito</p>
                <p className="text-lg font-bold text-gray-900">{formatCOP(results.loanAmount)}</p>
              </div>
              <div className="col-span-2 md:col-span-1">
                <p className="text-xs text-gray-500 mb-1">Cuota mensual</p>
                <p className="text-xl font-bold text-primary">{formatCOP(results.monthlyPayment)}</p>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-primary/20 text-sm text-gray-600">
              <span>Total a pagar: {formatCOP(results.totalPayment)}</span>
              <span className="mx-2">·</span>
              <span>Intereses: {formatCOP(results.totalInterest)}</span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
