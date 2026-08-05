import { Check } from 'lucide-react';

export function Stepper({ steps, currentStep = 1, className = '' }) {
  return (
    <div className={`flex items-center justify-between ${className}`}>
      {steps.map((step, index) => {
        const stepNumber = index + 1;
        const isCompleted = stepNumber < currentStep;
        const isCurrent = stepNumber === currentStep;
        const isLast = index === steps.length - 1;

        return (
          <div key={index} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center font-medium text-sm
                  transition-all duration-200
                  ${isCompleted
                    ? 'bg-success text-white'
                    : isCurrent
                      ? 'bg-primary text-white'
                      : 'bg-gray-200 text-gray-500'
                  }
                `}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4" />
                ) : (
                  stepNumber
                )}
              </div>
              <span
                className={`
                  mt-1 text-xs font-medium
                  ${isCurrent ? 'text-primary' : 'text-gray-500'}
                `}
              >
                {step}
              </span>
            </div>
            {!isLast && (
              <div
                className={`
                  flex-1 h-0.5 mx-2
                  ${isCompleted ? 'bg-success' : 'bg-gray-200'}
                `}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default Stepper;
