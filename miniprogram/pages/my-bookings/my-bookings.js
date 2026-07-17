const app = getApp()

Page({
  data: {
    bookings: [],
    filteredBookings: [],
    currentFilter: 'all',
    showRate: false,
    ratingBookingId: null,
    rating: 5,
    review: ''
  },

  onLoad: function () {
    this.loadBookings()
  },

  onShow: function () {
    this.loadBookings()
  },

  updateFilteredBookings: function () {
    const { bookings, currentFilter } = this.data
    let filtered = []
    if (currentFilter === 'all') {
      filtered = bookings
    } else {
      filtered = bookings.filter(b => b.status === currentFilter)
    }
    this.setData({
      filteredBookings: filtered
    })
  },

  loadBookings: function () {
    app.request({
      url: '/bookings'
    }).then((data) => {
      console.log('预约数据:', data)
      this.setData({
        bookings: data
      }, () => {
        this.updateFilteredBookings()
      })
    }).catch((err) => {
      console.error('加载预约失败:', err)
      this.setData({
        bookings: []
      }, () => {
        this.updateFilteredBookings()
      })
    })
  },

  setFilter: function (e) {
    this.setData({
      currentFilter: e.currentTarget.dataset.filter
    }, () => {
      this.updateFilteredBookings()
    })
  },



  getStatusText: function (status) {
    const map = {
      pending: '待确认',
      confirmed: '已确认',
      completed: '已完成',
      cancelled: '已取消',
      rejected: '已拒绝'
    }
    return map[status] || status
  },

  getStatusClass: function (status) {
    const map = {
      pending: 'warning',
      confirmed: 'success',
      completed: 'success',
      cancelled: 'danger',
      rejected: 'danger'
    }
    return map[status] || ''
  },

  cancelBooking: function (e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认取消',
      content: '确定要取消这个预约吗？',
      success: (res) => {
        if (res.confirm) {
          app.request({
            url: `/booking/${id}`,
            method: 'DELETE'
          }).then(() => {
            wx.showToast({ title: '取消成功', icon: 'success' })
            this.loadBookings()
          }).catch((err) => {
            wx.showToast({ title: err, icon: 'none' })
          })
        }
      }
    })
  },

  showRateModal: function (e) {
    this.setData({
      showRate: true,
      ratingBookingId: e.currentTarget.dataset.id,
      rating: 5,
      review: ''
    })
  },

  hideRateModal: function () {
    this.setData({
      showRate: false,
      ratingBookingId: null
    })
  },

  stopPropagation: function () {},

  setRating: function (e) {
    this.setData({
      rating: parseInt(e.currentTarget.dataset.rating)
    })
  },

  onReviewInput: function (e) {
    this.setData({
      review: e.detail.value
    })
  },

  submitRate: function () {
    app.request({
      url: `/booking/${this.data.ratingBookingId}/rate`,
      method: 'POST',
      data: {
        rating: this.data.rating,
        review: this.data.review
      }
    }).then(() => {
      wx.showToast({ title: '评价成功', icon: 'success' })
      this.hideRateModal()
      this.loadBookings()
    }).catch((err) => {
      wx.showToast({ title: err, icon: 'none' })
    })
  }
})