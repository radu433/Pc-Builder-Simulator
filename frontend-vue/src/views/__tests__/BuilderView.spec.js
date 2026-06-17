import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BuilderView from '../BuilderView.vue'

// Mocking axios ca sa nu faca apeluri reale la backend
vi.mock('axios', () => {
  return {
    default: {
      create: vi.fn(() => ({
        get: vi.fn(() => Promise.resolve({ data: { results: [] } })),
        post: vi.fn(() => Promise.resolve({ data: {} })),
        interceptors: {
          request: { use: vi.fn(), eject: vi.fn() },
          response: { use: vi.fn(), eject: vi.fn() }
        }
      })),
      get: vi.fn(() => Promise.resolve({ data: { results: [] } })),
      post: vi.fn(() => Promise.resolve({ data: {} }))
    }
  }
})

describe('BuilderView', () => {
  it('se randeaza corect si contine textul ESTIMATED TOTAL', () => {
    const wrapper = mount(BuilderView)
    
    // Verificam ca in header-ul builderului exista sectiunea cu totalul
    expect(wrapper.text()).toContain('ESTIMATED TOTAL')
  })

  it('incepe cu un pret total de 0 RON', () => {
    const wrapper = mount(BuilderView)
    
    // Gasim elementul care afiseaza pretul, in cazul nostru are clasa .price-value
    const priceElement = wrapper.find('.price-value')
    expect(priceElement.exists()).toBe(true)
    expect(priceElement.text()).toContain('0.00 RON')
  })

  it('schimba categoria activa cand se apasa pe un tab de componenta', async () => {
    const wrapper = mount(BuilderView)
    
    // Gasim butonul pentru CPU (presupunand ca primul e procesorul sau are o clasa)
    const cpuCategoryBtn = wrapper.findAll('.component-row').at(0)
    
    if (cpuCategoryBtn) {
        await cpuCategoryBtn.trigger('click')
        
        // Verificam daca starea de loading apare sau daca se schimba category
        // Avand in vedere ca in componenta originala cand apsam un row se apeleaza fetchCategoryParts, ar trebui sa treaca in starea de loading
        expect(wrapper.vm.loading).toBe(true)
        expect(wrapper.vm.activeCategoryId).toBe('cpu')
    }
  })
})
