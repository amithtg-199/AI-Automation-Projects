import React from 'react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: any;
}

export function ReviewModal({ isOpen, onClose, data }: ReviewModalProps) {
  if (!isOpen) return null;

  return (
    <Modal
      title="Review API Test Generation Plan"
      isOpen={isOpen}
      onClose={onClose}
    >
      <div className="space-y-4">
        <p className="text-sm text-secondary">
          The API automation agent has mapped your requirements and detected the following structure. Please review before generating code.
        </p>

        {data.map((pair: any, idx: number) => (
          <div key={idx} className="bg-elevated border border-border p-3 rounded text-sm">
            <h4 className="font-semibold mb-2">Lifecycle Pair {idx + 1}</h4>
            <div className="flex justify-between border-b border-border pb-1 mb-1">
              <span className="text-secondary">Create:</span>
              <span className="font-mono">{pair.create?.method} {pair.create?.url}</span>
            </div>
            <div className="flex justify-between border-b border-border pb-1 mb-1">
              <span className="text-secondary">Delete:</span>
              <span className="font-mono">{pair.delete?.method} {pair.delete?.url}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-secondary">Confidence Score:</span>
              <span className={pair.confidence > 0.7 ? "text-success" : "text-warning"}>
                {pair.confidence * 100}%
              </span>
            </div>
          </div>
        ))}
        
        {(!data || data.length === 0) && (
          <div className="text-sm text-secondary text-center p-4 border border-border rounded bg-elevated">
            No lifecycle pairs (Create/Delete) detected.
          </div>
        )}

        <div className="flex justify-end gap-2 pt-4">
          <Button variant="secondary" onClick={onClose}>Reject</Button>
          <Button onClick={() => {
            alert('Confirmed! Generating tests...');
            onClose();
          }}>Confirm & Generate</Button>
        </div>
      </div>
    </Modal>
  );
}
